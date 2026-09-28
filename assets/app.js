(() => {
  "use strict";
  const ACCESS_CODE = "BODA";
  const ACCESS_KEY = "boda_access_v2";
  const OUTBOX_KEY = "boda_rsvp_outbox_v2";
  const API_BASE = (document.querySelector('meta[name="wedding-api"]')?.content || "").replace(/\/+$/,"");
  const PUBLIC_API_BASE = (document.querySelector('meta[name="wedding-public-api"]')?.content || API_BASE).replace(/\/+$/, "");
  const DEFAULTS = {
    event_at:"2026-12-18T17:00:00-03:00",
    location_display:"San Pablo de Reyes · Jujuy",
    rsvp_deadline_display:"1 de diciembre",
    ceremony:{time:"17:00",title:"Santa Misa de Casamiento",place:"Iglesia San Pedro y San Pablo",address:"Carlos Figueroa · San Pablo de Reyes · Jujuy",lat:-24.14581,lng:-65.39445},
    celebration:{time:"19:00",title:"Recepción, cena & fiesta",place:"Quincho · San Pablo de Reyes",address:"A unos 300 metros de la ceremonia.",lat:-24.14816,lng:-65.39326},
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
  const cloneConfig = value => JSON.parse(JSON.stringify(value));
  let config = cloneConfig(DEFAULTS);
  let opening = false;
  let accessGranted = false;
  let configReady = false;
  let configRequest = null;
  let flushingOutbox = false;
  let memoryOutbox = [];
  let pendingSubmission = null;
  const $ = id => document.getElementById(id);
  const safeText = (id,v) => { const el=$(id); if(el && v!==undefined && v!==null) el.textContent=v; };
  const money = n => new Intl.NumberFormat("es-AR",{style:"currency",currency:"ARS",maximumFractionDigits:0}).format(Number(n)||0);

  document.addEventListener("DOMContentLoaded", () => {
    $("gateForm").addEventListener("submit", onGate);
    $("configRetry")?.addEventListener("click",()=>{ if(accessGranted) refreshPublicConfig(); });
    $("configRetryInline")?.addEventListener("click",()=>refreshPublicConfig());
    document.querySelectorAll('input[name="attendance"]').forEach(x=>x.addEventListener("change", syncAttendance));
    $("rsvpForm").addEventListener("submit", onRsvp);
    ["fullName","phone","email"].forEach(id=>$(id).addEventListener("blur",syncSeatLimit));
    document.querySelectorAll(".celebrate-link").forEach(a=>a.addEventListener("click",()=>celebrate(20)));
    document.querySelectorAll("[data-copy]").forEach(b=>b.addEventListener("click",()=>copyField(b.dataset.copy,b)));
    try{ if(sessionStorage.getItem(ACCESS_KEY)==="ok") unlock(false); }catch(_){}
    window.addEventListener("message",e=>{
      if(e.origin===API_BASE && e.data?.type==="wedding-admin-preview") unlock(false);
    });
    window.addEventListener("online", flushOutbox);
    function refreshCurrentConfig(){
      if(document.hidden || !accessGranted) return;
      refreshPublicConfig();
    }
    setInterval(refreshCurrentConfig,60000);
    setInterval(()=>{ if(!configReady) refreshCurrentConfig(); },15000);
    setInterval(()=>{ if(accessGranted && !document.hidden) flushOutbox().catch(()=>{}); },30000);
    window.addEventListener("online",refreshCurrentConfig);
    window.addEventListener("pageshow",refreshCurrentConfig);
    document.addEventListener("visibilitychange",refreshCurrentConfig);
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
    const code=raw.replace(/[\s\u200B-\u200D\u2060\uFEFF]/g,"").toUpperCase();
    if(code!==ACCESS_CODE){
      $("gateError").textContent="Ese código no coincide. Probá de nuevo.";
      $("gateCode").select();
      return;
    }
    try{ sessionStorage.setItem(ACCESS_KEY,"ok"); }catch(_){}
    unlock(true);
  }

  // The social access code is independent of remote configuration availability.
  // Never keep a guest outside because a separate network request is slow/down.
  async function unlock(withCelebration){
    if(opening || !$("site").classList.contains("hidden")) return;
    accessGranted = true;
    opening = true;
    if(!configReady){
      ["ceremonyTime","celebrationTime","rsvpDeadline"].forEach(id=>safeText(id,"Actualizando…"));
      $("ticketCard")?.classList.add("hidden");
      $("paymentCard")?.classList.add("hidden");
    }
    $("gateError").textContent="";
    $("gate").classList.add("hidden");
    $("site").classList.remove("hidden");
    document.body.classList.remove("locked");
    opening = false;
    refreshPublicConfig();
    if(withCelebration) requestAnimationFrame(()=>celebrate(42));
    startCountdown();
    loadInstagram().catch(()=>{});
    flushOutbox().catch(()=>{});
  }

  function configNotice(state){
    const box=$("configStatus"), retry=$("configRetryInline");
    if(box) box.classList.toggle("hidden",state==="ready");
    if(retry) retry.classList.toggle("hidden",state!=="error");
    safeText("configStatusText",state==="error"
      ? "La invitación está abierta. No pudimos actualizar los datos; volveremos a intentarlo automáticamente."
      : "Estamos cargando los horarios y datos actualizados de la invitación…");
  }

  function refreshPublicConfig(){
    if(configRequest) return configRequest;
    if(!configReady) configNotice("loading");
    configRequest=loadPublicConfig().then(()=>{
      configReady=true;
      configNotice("ready");
      return true;
    }).catch(()=>{
      configNotice("error");
      return false;
    }).finally(()=>{ configRequest=null; });
    return configRequest;
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
    let lastError;
    for(let attempt=0; attempt<3; attempt++){
      const ctrl=new AbortController();
      const timer=setTimeout(()=>ctrl.abort(),timeout);
      try{
        const res=await fetch(url,{...options,signal:ctrl.signal});
        const body=await res.json();
        if(!res.ok){
          const error=new Error(body.error||`HTTP ${res.status}`);
          error.status=res.status;
          throw error;
        }
        return body;
      }catch(err){
        lastError=err;
        if(err.status>=400 && err.status<500) throw err;
        if(attempt<2) await new Promise(resolve=>setTimeout(resolve,500*(attempt+1)));
      }finally{ clearTimeout(timer); }
    }
    throw lastError || new Error("request_failed");
  }

  async function loadPublicConfig(){
    if(!PUBLIC_API_BASE) throw new Error("missing_config_source");
    const remote=await fetchJson(`${PUBLIC_API_BASE}/api/public/config`,{cache:"no-store"},15000);
    if(!remote || typeof remote!=="object" || !remote.ticket ||
       typeof remote.ticket.enabled!=="boolean" ||
       (remote.ticket.enabled && (typeof remote.ticket.price!=="number" || !Number.isFinite(remote.ticket.price))) ||
       !remote.copy || !remote.ceremony || !remote.celebration){
      throw new Error("invalid_public_config");
    }
    config=merge(DEFAULTS,remote);
    applyConfig(config);
    configReady=true;
  }

  function merge(base, extra){
    const out=cloneConfig(base);
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
    syncSeatLimit();
    safeText("seatsLabel","Cantidad total de personas (incluyéndote)");
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
    const nodes=sections.map(item=>document.getElementById(item.id)).filter(Boolean);
    const current=Array.from(main.children).filter(node=>nodes.includes(node));
    // Moving an existing section detaches its inputs and closes mobile keyboards.
    // Preserve the DOM when the layout order did not actually change.
    if(nodes.some((node,index)=>current[index]!==node || node.parentNode!==main)){
      nodes.forEach(node=>main.appendChild(node));
    }
    sections.forEach(item=>{
      const section=document.getElementById(item.id); if(!section)return;
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
    const embed=`https://www.google.com/maps?q=${encodeURIComponent(q)}&z=17&output=embed`;
    if(iframe && iframe.getAttribute("src")!==embed) iframe.src=embed;
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

  function syncSeatLimit(){
    safeText("seatsHint","Indicá el total de personas que asistirán, incluyéndote. Sin límite de acompañantes.");
  }

  function syncAttendance(){
    const yes=document.querySelector('input[name="attendance"]:checked')?.value==="yes";
    $("attendingFields").classList.toggle("hidden",!yes);
    $("declineMessage").classList.toggle("hidden",yes);
    $("ticketCard").classList.toggle("hidden",!configReady || !yes || config.ticket?.enabled===false);
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
    let p=payloadFromForm();
    const matching=entry=>submissionSignature(entry)===submissionSignature(p);
    if(pendingSubmission && matching(pendingSubmission)) p=pendingSubmission;
    else p=readOutbox().find(matching)||p;
    const status=$("rsvpStatus"), btn=$("rsvpSubmit");
    if(btn.disabled) return;
    if(!p.name){ showStatus("Decinos tu nombre y apellido para guardar la respuesta.",false); $("fullName").focus(); return; }
    if(p.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(p.email)){ showStatus("Revisá el email: parece incompleto.",false); $("email").focus(); return; }
    if(p.attendance==="yes" && (!$("seats").checkValidity() || !Number.isSafeInteger(p.seats))){ showStatus("Ingresá una cantidad entera de personas, desde 1.",false); return; }
    pendingSubmission=p;
    btn.disabled=true; btn.textContent="Enviando…";
    try{
      if(!PUBLIC_API_BASE) throw new Error("API no configurada");
      const receipt=await fetchJson(`${PUBLIC_API_BASE}/api/public/rsvp`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(p)
      },5500);
      if(receipt?.ok!==true || typeof receipt.id!=="string" || !receipt.id) throw new Error("invalid_receipt");
      acknowledgeSubmission(p,p.attendance==="yes" ? "Listo. Quedó confirmada tu asistencia. ¡Nos vemos el 18!" : "Listo. Gracias por avisarnos; quedó registrada tu respuesta.");
      if(p.attendance==="yes") celebrate(34);
    }catch(err){
      if(err.status>=400 && err.status<500 && err.status!==429){
        showStatus("El servidor no aceptó la respuesta. Revisá los datos y volvé a enviarla; todavía no está confirmada.",false);
        return;
      }
      const persisted=enqueue(p);
      const phone=(config.fallback_whatsapp||"").replace(/\D/g,"");
      showStatus(persisted
        ? "Todavía no recibimos la confirmación del servidor. La respuesta quedó pendiente en este dispositivo y la reintentaremos automáticamente."
        : "Todavía no recibimos la confirmación del servidor. Este navegador no permite guardar la respuesta: dejá esta página abierta y reintentaremos sin borrar el formulario.",false);
      if(phone){
        const a=document.createElement("a");
        a.href=`https://wa.me/${phone}?text=${encodeURIComponent(whatsappText(p))}`;
        a.target="_blank";a.rel="noopener";a.textContent=" Enviar por WhatsApp";
        status.appendChild(a);
      }
    }finally{
      btn.disabled=false; btn.textContent="Enviar confirmación";
    }
  }

  function submissionSignature(p){
    return JSON.stringify([p.name,p.phone,p.email,p.attendance,p.seats,p.diet,p.song,p.message]);
  }

  function acknowledgeSubmission(p,message){
    const current=payloadFromForm();
    const unchanged=submissionSignature(current)===submissionSignature(p);
    const hasDraft=Boolean(current.name || current.phone || current.email || current.diet || current.song || current.message || current.seats!==1 || current.attendance!=="yes");
    removeFromOutbox(new Set([p.request_id]));
    if(pendingSubmission?.request_id===p.request_id) pendingSubmission=null;
    if(unchanged){ $("rsvpForm").reset(); syncAttendance(); }
    // A delayed receipt belongs to the submitted snapshot, not subsequent typing.
    showStatus(!unchanged && hasDraft
      ? "La respuesta enviada quedó guardada. Los cambios actuales del formulario todavía no se enviaron."
      : message,unchanged || !hasDraft);
  }

  function showStatus(text,ok){
    const el=$("rsvpStatus"); el.textContent=text; el.className=`form-status ${ok?"ok":"err"}`;
  }

  function readOutbox(){
    let saved=[];
    try{const value=JSON.parse(localStorage.getItem(OUTBOX_KEY)||"[]");if(Array.isArray(value)) saved=value;}catch(_){}
    const byId=new Map();
    [...saved,...memoryOutbox].forEach(p=>{if(p && typeof p.request_id==="string") byId.set(p.request_id,p);});
    return Array.from(byId.values());
  }

  function writeOutbox(items){
    memoryOutbox=items;
    try{localStorage.setItem(OUTBOX_KEY,JSON.stringify(items));return true;}catch(_){return false;}
  }

  function enqueue(p){
    const items=readOutbox();
    if(!items.some(x=>x.request_id===p.request_id)) items.push(p);
    return writeOutbox(items);
  }

  function removeFromOutbox(ids){
    // Re-read after network waits so a newer submission is never overwritten.
    writeOutbox(readOutbox().filter(p=>!ids.has(p.request_id)));
  }

  async function flushOutbox(){
    if(flushingOutbox || !PUBLIC_API_BASE || !navigator.onLine) return;
    const items=readOutbox();
    if(!items.length) return;
    flushingOutbox=true;
    try{
      for(const p of items){
        try{
          const receipt=await fetchJson(`${PUBLIC_API_BASE}/api/public/rsvp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)},4000);
          if(receipt?.ok!==true || typeof receipt.id!=="string" || !receipt.id) throw new Error("invalid_receipt");
          acknowledgeSubmission(p,"La conexión se recuperó y el servidor guardó tu respuesta.");
        }catch(_){}
      }
    }finally{flushingOutbox=false;}
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
    if(!section || !PUBLIC_API_BASE) return;
    try{
      const feed=await fetchJson(`${PUBLIC_API_BASE}/api/public/instagram`,{cache:"no-store"},4000);
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
      section.classList.toggle("hidden",section.dataset.layoutHidden==="true");
    }catch(_){}
  }

  async function copyField(id,button){
    const value=$(id)?.textContent?.trim(); if(!value) return;
    try{ await navigator.clipboard.writeText(value); button.textContent="Copiado"; setTimeout(()=>button.textContent="Copiar",1300); }catch(_){}
  }
})();
