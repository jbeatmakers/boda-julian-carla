(() => {
  "use strict";
  const ACCESS_CODE = "BODA";
  const ACCESS_KEY = "boda_access_v2";
  const OUTBOX_KEY = "boda_rsvp_outbox_v2";
  const API_BASE = (document.querySelector('meta[name="wedding-api"]')?.content || "").replace(/\/+$/,"");
  const DEFAULTS = {
    event_at:"2026-12-18T17:00:00-03:00",
    location_display:"San Pablo de Reyes · Jujuy",
    rsvp_deadline_display:"1 de diciembre",
    ceremony:{time:"17:00",title:"Santa Misa de Casamiento",place:"Iglesia San Pedro y San Pablo",address:"Carlos Figueroa · San Pablo de Reyes · Jujuy",lat:-24.14581,lng:-65.39445},
    celebration:{time:"18:30",title:"Recepción, cena & fiesta",place:"Quincho · San Pablo de Reyes",address:"A unos 300 metros de la ceremonia.",lat:-24.14816,lng:-65.39326},
    dress:{title:"Estética Edén",concept:"Una gala fresca, sofisticada y luminosa, inspirada en la naturaleza al atardecer.",details:"Formal elegante. No hace falta comprar de nuevo: un buen accesorio puede terminar de llevar el conjunto al tono de la noche."},
    ticket:{enabled:false,price:null,currency:"ARS",text:""},
    bank:{holder:"",alias:"",cbu:"",mp_url:""},
    fallback_whatsapp:"",
    layout:{sections:[
      {id:"lugares",label:"Horarios y mapas",visible:true},
      {id:"dress",label:"Dress code",visible:true},
      {id:"rsvp",label:"Confirmación de asistencia",visible:true},
      {id:"regalos",label:"Tarjeta y regalos",visible:true},
      {id:"instagramSection",label:"Instagram",visible:true}
    ]}
  };
  let config = structuredClone(DEFAULTS);
  let opening = false;
  const $ = id => document.getElementById(id);
  const safeText = (id,v) => { const el=$(id); if(el && v!==undefined && v!==null) el.textContent=v; };
  const money = n => new Intl.NumberFormat("es-AR",{style:"currency",currency:"ARS",maximumFractionDigits:0}).format(Number(n)||0);

  document.addEventListener("DOMContentLoaded", () => {
    $("gateForm").addEventListener("submit", onGate);
    $("configRetry").addEventListener("click",()=>unlock(false));
    document.querySelectorAll('input[name="attendance"]').forEach(x=>x.addEventListener("change", syncAttendance));
    $("rsvpForm").addEventListener("submit", onRsvp);
    ["fullName","phone","email"].forEach(id=>$(id).addEventListener("blur",syncSeatLimit));
    document.querySelectorAll(".celebrate-link").forEach(a=>a.addEventListener("click",()=>celebrate(20)));
    document.querySelectorAll("[data-copy]").forEach(b=>b.addEventListener("click",()=>copyField(b.dataset.copy,b)));
    if(sessionStorage.getItem(ACCESS_KEY)==="ok") unlock(false);
    window.addEventListener("message",e=>{
      if(e.origin===API_BASE && e.data?.type==="wedding-admin-preview") unlock(false);
    });
    window.addEventListener("online", flushOutbox);
  });

  async function onGate(e){
    e.preventDefault();
    const raw=($("gateCode").value||"").trim();
    if(raw.startsWith("#")){
      if(!API_BASE){ $("gateError").textContent="El administrador no está disponible en este momento."; return; }
      $("gateError").textContent="Abriendo administración…";
      try{
        const res=await fetch(`${API_BASE}/api/admin/entry`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code:raw})});
        const data=await res.json().catch(()=>({}));
        if(!res.ok || !data.entry_token) throw new Error(data.error||"entry_failed");
        window.location.href=`${API_BASE}/?entry=${encodeURIComponent(data.entry_token)}`;
      }catch(_){
        $("gateError").textContent="No pude abrir la administración. Probá nuevamente.";
        $("gateCode").select();
      }
      return;
    }
    const code=raw.toUpperCase();
    if(code!==ACCESS_CODE){
      $("gateError").textContent="Ese código no coincide. Probá de nuevo.";
      $("gateCode").select();
      return;
    }
    sessionStorage.setItem(ACCESS_KEY,"ok");
    unlock(true);
  }

  async function unlock(withCelebration){
    if(opening || !$("site").classList.contains("hidden")) return;
    opening = true;
    $("configRetry").classList.add("hidden");
    $("gateError").textContent="Cargando la invitación actual…";
    try{
      await loadPublicConfig();
    }catch(_){
      $("gateError").textContent="No pudimos cargar la invitación. Revisá tu conexión y volvé a intentar.";
      $("configRetry").classList.remove("hidden");
      return;
    }finally{ opening = false; }
    $("gateError").textContent="";
    $("gate").classList.add("hidden");
    $("site").classList.remove("hidden");
    document.body.classList.remove("locked");
    if(withCelebration) requestAnimationFrame(()=>celebrate(42));
    startCountdown();
    loadInstagram();
    flushOutbox();
  }

  function celebrate(count=32){
    if(matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const layer=document.createElement("div");
    layer.className="confetti-layer";
    const palette=["#7c8b6f","#4a5844","#ae603f","#d7be78","#f4e7cf"];
    for(let i=0;i<count;i++){
      const p=document.createElement("i");
      p.className="confetti-piece";
      p.style.left=(3+Math.random()*94)+"vw";
      p.style.background=palette[i%palette.length];
      p.style.setProperty("--dur",(1.25+Math.random()*.9)+"s");
      p.style.setProperty("--drift",(-90+Math.random()*180)+"px");
      p.style.setProperty("--rot",(Math.random()*180)+"deg");
      p.style.animationDelay=(Math.random()*.2)+"s";
      layer.appendChild(p);
    }
    document.body.appendChild(layer);
    setTimeout(()=>layer.remove(),2400);
  }

  async function fetchJson(url, options={}, timeout=4500){
    const ctrl=new AbortController();
    const timer=setTimeout(()=>ctrl.abort(),timeout);
    try{
      const res=await fetch(url,{...options,signal:ctrl.signal});
      const body=await res.json().catch(()=>({}));
      if(!res.ok) throw new Error(body.error||`HTTP ${res.status}`);
      return body;
    } finally { clearTimeout(timer); }
  }

  async function loadPublicConfig(){
    if(!API_BASE) throw new Error("missing_config_source");
    const remote=await fetchJson(`${API_BASE}/api/public/config`,{cache:"no-store"},15000);
    if(!remote || typeof remote!=="object" || !remote.ticket ||
       typeof remote.ticket.enabled!=="boolean" ||
       (remote.ticket.enabled && (typeof remote.ticket.price!=="number" || !Number.isFinite(remote.ticket.price))) ||
       !remote.copy || !remote.ceremony || !remote.celebration){
      throw new Error("invalid_public_config");
    }
    config=merge(DEFAULTS,remote);
    applyConfig(config);
  }

  function merge(base, extra){
    const out=structuredClone(base);
    for(const [k,v] of Object.entries(extra||{})){
      if(v && typeof v==="object" && !Array.isArray(v) && out[k] && typeof out[k]==="object") out[k]={...out[k],...v};
      else if(v!==undefined) out[k]=v;
    }
    return out;
  }

  function applyConfig(c){
    const editable=c.copy||{};
    document.querySelectorAll("[data-site-copy]").forEach(el=>{
      const key=el.dataset.siteCopy,value=editable[key];
      if(value!==undefined && value!==null) el.textContent=value;
    });
    document.querySelectorAll("[data-site-copy-placeholder]").forEach(el=>{
      const value=editable[el.dataset.siteCopyPlaceholder];
      if(value!==undefined && value!==null) el.placeholder=value;
    });
    applyLayout(c.layout);
    safeText("heroLocation",c.location_display);
    safeText("rsvpDeadline",c.rsvp_deadline_display);
    if(c.ceremony){
      safeText("ceremonyTime",c.ceremony.time); safeText("ceremonyTitle",c.ceremony.title);
      safeText("ceremonyPlace",c.ceremony.place); safeText("ceremonyAddress",c.ceremony.address);
      setMap("ceremony",c.ceremony.lat,c.ceremony.lng);
    }
    if(c.celebration){
      safeText("celebrationTime",c.celebration.time); safeText("celebrationTitle",c.celebration.title);
      safeText("celebrationPlace",c.celebration.place); safeText("celebrationAddress",c.celebration.address);
      setMap("celebration",c.celebration.lat,c.celebration.lng);
    }
    if(c.dress){
      safeText("dressTitle",c.dress.title); safeText("dressConcept",c.dress.concept); safeText("dressDetails",c.dress.details);
    }
    const ticket=$("ticketCard");
    const attending=document.querySelector('input[name="attendance"]:checked')?.value!=="no";
    ticket.classList.toggle("hidden",c.ticket?.enabled===false || !attending);
    if(c.ticket?.enabled!==false){
      safeText("ticketPrice",money(c.ticket?.price||0));
      safeText("ticketText",c.ticket?.text);
    }
    const bank=c.bank||{}, payment=$("paymentCard");
    const hasBank=Boolean(bank.alias||bank.cbu||bank.mp_url);
    payment.classList.toggle("hidden",!hasBank);
    safeText("bankHolder",bank.holder); safeText("bankAlias",bank.alias); safeText("bankCbu",bank.cbu);
    const mp=$("mpLink");
    if(bank.mp_url){ mp.href=bank.mp_url; mp.classList.remove("hidden"); } else mp.classList.add("hidden");
  }

  function applyLayout(layout){
    const main=document.querySelector("#site main"),defaults=DEFAULTS.layout.sections;
    if(!main)return;
    const configured=Array.isArray(layout?.sections)?layout.sections:[];
    const byId=new Map(configured.map(x=>[x.id,x]));
    const sections=defaults.map(x=>byId.get(x.id)||x);
    configured.forEach(x=>{if(!sections.some(s=>s.id===x.id))sections.push(x);});
    sections.forEach(item=>{
      const section=document.getElementById(item.id); if(!section)return;
      main.appendChild(section);
      const hidden=item.visible===false;
      section.dataset.layoutHidden=hidden?"true":"false";
      section.classList.toggle("hidden",hidden || (section.id==="instagramSection" && !section.dataset.hasInstagram));
    });
  }

  function setMap(prefix,lat,lng){
    if(!Number.isFinite(Number(lat))||!Number.isFinite(Number(lng))) return;
    const q=`${Number(lat)},${Number(lng)}`;
    const iframe=$(prefix+"Map"), link=$(prefix+"Directions"), address=$(prefix+"Address");
    const directions=`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`;
    if(iframe) iframe.src=`https://www.google.com/maps?q=${encodeURIComponent(q)}&z=17&output=embed`;
    if(link) link.href=directions;
    if(address && address.tagName==="A") address.href=directions;
  }

  function startCountdown(){
    const tick=()=>{
      const target=new Date(config.event_at||DEFAULTS.event_at).getTime();
      const diff=Math.max(0,target-Date.now());
      const vals={
        cdDays:Math.floor(diff/86400000),
        cdHours:Math.floor(diff%86400000/3600000),
        cdMinutes:Math.floor(diff%3600000/60000),
        cdSeconds:Math.floor(diff%60000/1000)
      };
      Object.entries(vals).forEach(([id,v])=>safeText(id,String(v).padStart(2,"0")));
      if(diff===0) safeText("countdown","¡Hoy es el gran día!");
    };
    tick(); setInterval(tick,1000);
  }

  async function syncSeatLimit(){
    const select=$("seats"), hint=$("seatsHint");
    const identity={name:$("fullName").value.trim(),phone:$("phone").value.trim(),email:$("email").value.trim()};
    let maxSeats=1, found=false;
    if(API_BASE && (identity.name.length>1 || identity.phone || identity.email)){
      try{
        const r=await fetchJson(`${API_BASE}/api/public/invite`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(identity)},3000);
        maxSeats=Math.max(1,Math.min(12,Number(r.max_seats)||1)); found=!!r.found;
      }catch(_){}
    }
    const current=Math.min(maxSeats,Math.max(1,Number(select.value)||1));
    select.innerHTML=Array.from({length:maxSeats},(_,i)=>`<option value="${i+1}">${i+1} ${i===0?"persona":"personas"}</option>`).join("");
    select.value=String(current);
    hint.textContent=found ? `Tu invitación tiene hasta ${maxSeats} ${maxSeats===1?"lugar":"lugares"}.` : "La cantidad disponible se ajusta a tu invitación.";
  }

  function syncAttendance(){
    const yes=document.querySelector('input[name="attendance"]:checked')?.value==="yes";
    $("attendingFields").classList.toggle("hidden",!yes);
    $("declineMessage").classList.toggle("hidden",yes);
    $("ticketCard").classList.toggle("hidden",!yes || config.ticket?.enabled===false);
    if(yes) syncSeatLimit();
  }

  function clientId(){
    return (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`);
  }

  function payloadFromForm(){
    const attendance=document.querySelector('input[name="attendance"]:checked')?.value||"yes";
    return {
      request_id:clientId(),
      name:$("fullName").value.trim(),
      phone:$("phone").value.trim(),
      email:$("email").value.trim(),
      attendance,
      seats:attendance==="yes" ? Math.max(1,Number($("seats").value)||1) : 0,
      diet:attendance==="yes" ? $("diet").value.trim() : "",
      song:attendance==="yes" ? $("song").value.trim() : "",
      message:$("message").value.trim(),
      submitted_at:new Date().toISOString()
    };
  }

  async function onRsvp(e){
    e.preventDefault();
    const p=payloadFromForm(), status=$("rsvpStatus"), btn=$("rsvpSubmit");
    if(!p.name){ showStatus("Decinos tu nombre y apellido para guardar la respuesta.",false); $("fullName").focus(); return; }
    if(p.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(p.email)){ showStatus("Revisá el email: parece incompleto.",false); $("email").focus(); return; }
    btn.disabled=true; btn.textContent="Enviando…";
    try{
      if(!API_BASE) throw new Error("API no configurada");
      await fetchJson(`${API_BASE}/api/public/rsvp`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(p)
      },5500);
      showStatus(p.attendance==="yes" ? "Listo. Quedó confirmada tu asistencia. ¡Nos vemos el 18!" : "Listo. Gracias por avisarnos; quedó registrada tu respuesta.",true);
      if(p.attendance==="yes") celebrate(34);
      $("rsvpForm").reset(); syncAttendance();
    }catch(err){
      enqueue(p);
      const phone=(config.fallback_whatsapp||"").replace(/\D/g,"");
      if(phone){
        const wa=whatsappText(p);
        showStatus(`No pudimos conectar con el servidor en este momento. Guardamos tu respuesta en este dispositivo y podés asegurarla por WhatsApp: `,false);
        const a=document.createElement("a"); a.href=`https://wa.me/${phone}?text=${encodeURIComponent(wa)}`; a.target="_blank"; a.rel="noopener"; a.textContent="enviar confirmación"; a.style.fontWeight="600";
        status.appendChild(a);
      }else{
        showStatus("No pudimos conectar en este momento. Guardamos la respuesta en este dispositivo y la reintentaremos automáticamente cuando vuelva la conexión.",false);
      }
    }finally{
      btn.disabled=false; btn.textContent="Enviar confirmación";
    }
  }

  function showStatus(text,ok){
    const el=$("rsvpStatus"); el.textContent=text; el.className=`form-status ${ok?"ok":"err"}`;
  }

  function enqueue(p){
    try{
      const q=JSON.parse(localStorage.getItem(OUTBOX_KEY)||"[]");
      if(!q.some(x=>x.request_id===p.request_id)) q.push(p);
      localStorage.setItem(OUTBOX_KEY,JSON.stringify(q.slice(-20)));
    }catch(_){}
  }

  async function flushOutbox(){
    if(!API_BASE || !navigator.onLine) return;
    let q=[];
    try{ q=JSON.parse(localStorage.getItem(OUTBOX_KEY)||"[]"); }catch(_){}
    if(!q.length) return;
    const remaining=[];
    for(const p of q){
      try{
        await fetchJson(`${API_BASE}/api/public/rsvp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)},4000);
      }catch(_){ remaining.push(p); }
    }
    localStorage.setItem(OUTBOX_KEY,JSON.stringify(remaining));
  }

  function whatsappText(p){
    const lines=["Confirmación boda Julián & Carla",`Nombre: ${p.name}`,`Asistencia: ${p.attendance==="yes"?"Sí":"No"}`];
    if(p.attendance==="yes") lines.push(`Lugares: ${p.seats}`);
    if(p.diet) lines.push(`Menú: ${p.diet}`);
    if(p.song) lines.push(`Canción: ${p.song}`);
    if(p.message) lines.push(`Mensaje: ${p.message}`);
    return lines.join("\n");
  }

  async function loadInstagram(){
    const section=$("instagramSection");
    if(!section || !API_BASE) return;
    try{
      const feed=await fetchJson(`${API_BASE}/api/public/instagram`,{cache:"no-store"},4000);
      const items=Array.isArray(feed.items)?feed.items:[];
      const username=String(feed.username||"juli.y.carli").replace(/^@/,"");
      const profileUrl=feed.profile_url||`https://www.instagram.com/${username}/`;
      if(!profileUrl && !items.length) return;
      section.dataset.hasInstagram="true";
      if(section.dataset.layoutHidden!=="true") section.classList.remove("hidden");
      safeText("instagramHeading",feed.heading||"Nuestro Instagram");
      safeText("instagramIntro",feed.intro||"Seguinos para acompa\u00f1arnos en la previa y revivir la fiesta.");
      const grid=$("instagramGrid"); grid.textContent="";
      if(items.length){
        items.slice(0,6).forEach(item=>{
          const href=item.permalink||profileUrl, media=item.thumbnail_url||item.media_url;
          if(!href || !media) return;
          const a=document.createElement("a"); a.className="instagram-card"; a.href=href; a.target="_blank"; a.rel="noopener noreferrer";
          const img=document.createElement("img"); img.loading="lazy"; img.src=media; img.alt=(item.caption||"Publicaci\u00f3n de Instagram").slice(0,120); a.appendChild(img);
          if(item.media_type==="VIDEO"){ const b=document.createElement("span"); b.className="instagram-badge"; b.textContent="Reel \u25b6"; a.appendChild(b); }
          grid.appendChild(a);
        });
      }else{
        const empty=document.createElement("div"); empty.className="instagram-empty card";
        const strong=document.createElement("strong"); strong.textContent=`@${username}`;
        const text=document.createElement("p"); text.className="muted"; text.textContent="Todav\u00eda no hay publicaciones. Cuando empecemos a compartir fotos y videos, van a aparecer ac\u00e1 autom\u00e1ticamente.";
        empty.append(strong,text); grid.appendChild(empty);
      }
      const profile=$("instagramProfile");
      if(profileUrl){profile.href=profileUrl;profile.textContent=`Abrir @${username} en Instagram \u2197`;profile.classList.remove("hidden");}
      section.classList.remove("hidden");
    }catch(_){}
  }

  async function copyField(id,button){
    const value=$(id)?.textContent?.trim(); if(!value) return;
    try{ await navigator.clipboard.writeText(value); button.textContent="Copiado"; setTimeout(()=>button.textContent="Copiar",1300); }catch(_){}
  }
})();
