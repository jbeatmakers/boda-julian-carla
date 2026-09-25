(()=>{
  "use strict";
  const $=id=>document.getElementById(id);
  let csrf="";
  let state={settings:{},dashboard:{},planner:{},guests:[],rsvp_submissions:[],expenses:[],shopping:[],tasks:[],vendors:[],songs:[],menu:[],contributions:[]};
  let scanStream=null,scanTimer=null;
  const COPY_FIELDS=[['gate_intro','Entrada · frase principal'],['gate_help','Entrada · ayuda'],['gate_label','Entrada · etiqueta del código'],['gate_submit','Entrada · botón'],['hero_intro','Portada · introducción'],['hero_confirm_btn','Portada · botón confirmar'],['hero_maps_btn','Portada · botón lugares'],['countdown_days','Cuenta regresiva · días'],['countdown_hours','Cuenta regresiva · horas'],['countdown_minutes','Cuenta regresiva · minutos'],['countdown_seconds','Cuenta regresiva · segundos'],['places_eyebrow','Lugares · etiqueta'],['places_title','Lugares · título'],['places_intro','Lugares · bajada'],['ceremony_eyebrow','Ceremonia · etiqueta'],['celebration_eyebrow','Celebración · etiqueta'],['maps_directions','Mapas · botón cómo llegar'],['dress_eyebrow','Dress code · etiqueta'],['rsvp_eyebrow','RSVP · etiqueta'],['rsvp_title','RSVP · título'],['rsvp_deadline_intro','RSVP · frase del vencimiento'],['attendance_yes','RSVP · opción sí'],['attendance_yes_label','RSVP · subtítulo sí'],['attendance_no','RSVP · opción no'],['attendance_no_label','RSVP · subtítulo no'],['name_label','RSVP · nombre'],['phone_label','RSVP · teléfono'],['email_label','RSVP · email'],['seats_label','RSVP · lugares'],['seats_hint','RSVP · ayuda lugares'],['diet_label','RSVP · alimentación'],['diet_placeholder','RSVP · placeholder alimentación'],['song_label','RSVP · canción'],['song_placeholder','RSVP · placeholder canción'],['decline_body','RSVP · mensaje si no asiste'],['decline_gift_note','RSVP · aclaración regalos'],['message_label','RSVP · dedicatoria'],['message_placeholder','RSVP · placeholder dedicatoria'],['submit_rsvp','RSVP · botón enviar'],['gift_eyebrow','Regalos · etiqueta'],['gift_title','Regalos · título'],['gift_intro','Regalos · introducción'],['ticket_eyebrow','Tarjeta · etiqueta'],['ticket_title','Tarjeta · título'],['present_eyebrow','Regalo · etiqueta'],['present_title','Regalo · título'],['present_body','Regalo · texto'],['present_transfer','Regalo · transferencia'],['transfer_eyebrow','Transferencia · etiqueta'],['transfer_holder','Transferencia · titular'],['transfer_alias','Transferencia · alias'],['transfer_cbu','Transferencia · CBU/CVU'],['copy_button','Transferencia · botón copiar'],['mercadopago_button','Transferencia · Mercado Pago'],['instagram_eyebrow','Instagram · etiqueta'],['instagram_title','Instagram · título'],['instagram_intro','Instagram · introducción'],['instagram_button','Instagram · botón'],['footer_date','Pie · fecha y lugar']];
  const LAYOUT_DEFAULTS=[['lugares','Horarios y mapas'],['dress','Dress code'],['rsvp','Confirmación de asistencia'],['regalos','Tarjeta y regalos'],['instagramSection','Instagram']];
  const PLAN_FIELDS=[['planned_guests_override','Personas para planificar (0 = automático)',1],['guest_buffer_pct','Margen extra %',1],['table_capacity','Personas por mesa',1],['drinkers_pct','Adultos que toman alcohol %',1],['water_l_pp','Agua L/persona',.1],['soft_l_pp','Gaseosa/mixer L/persona',.1],['beer_l_drinker','Cerveza L/bebedor',.1],['wine_l_drinker','Vino L/bebedor',.05],['sparkling_l_pp','Espumante L/persona',.025],['spirits_l_drinker','Destilado L/bebedor',.02],['ice_kg_pp','Hielo kg/persona',.1],['appetizer_pieces_pp','Bocados/persona',1],['main_portions_pp','Principal/persona',.05],['dessert_portions_pp','Postre/persona',.05],['cake_g_pp','Torta g/persona',10]];

  document.addEventListener("DOMContentLoaded",init);

  async function init(){
    bindStatic();
    ensureAccessibleNames();
    try{
      const s=await api("/api/admin/session");
      if(s.authenticated){csrf=s.csrf||"";showApp();await loadState();await loadInstagramAdminStatus();}
      else showLogin();
    }catch(e){showLogin();setLoginStatus("No se pudo conectar con el servidor de administración.");}
  }

  function bindStatic(){
    $("loginForm").addEventListener("submit",login);
    $("logoutBtn").addEventListener("click",logout);
    $("refreshBtn").addEventListener("click",loadState);
    $("backupBtn").addEventListener("click",downloadBackup);
    $("importFile").addEventListener("change",importBackup);
    $("csvBtn").addEventListener("click",downloadGuestsCsv);
    $("tabs").addEventListener("click",e=>{const b=e.target.closest("[data-tab]");if(b)openTab(b.dataset.tab);});
    $("guestSearch").addEventListener("input",renderGuests);
    $("guestFilter").addEventListener("change",renderGuests);
    $("guestGroupFilter").addEventListener("change",renderGuests);
    $("viewAdminBtn").addEventListener("click",()=>setViewMode("admin"));
    $("viewCardBtn").addEventListener("click",()=>setViewMode("card"));
    $("fullCardPreview").addEventListener("load",sendCardPreviewUnlock);
    $("addGuestBtn").addEventListener("click",()=>openGuest());
    $("closeGuestModal").addEventListener("click",closeGuest);
    $("cancelGuest").addEventListener("click",closeGuest);
    $("guestModal").addEventListener("click",e=>{if(e.target===$("guestModal"))closeGuest();});
    $("guestForm").addEventListener("submit",saveGuest);
    $("gTicketMode").addEventListener("change",syncTicketMode);
    $("expenseForm").addEventListener("submit",e=>createFromForm(e,"expenses"));
    $("shoppingForm").addEventListener("submit",e=>createFromForm(e,"shopping"));
    $("menuForm").addEventListener("submit",e=>createFromForm(e,"menu"));
    $("contributionForm").addEventListener("submit",e=>createFromForm(e,"contributions"));
    $("taskForm").addEventListener("submit",e=>createFromForm(e,"tasks"));
    $("seedTasksBtn").addEventListener("click",seedWeddingTasks);
    $("vendorForm").addEventListener("submit",e=>createFromForm(e,"vendors"));
    $("saveSettingsBtn").addEventListener("click",saveSettings);
    $("savePlanningBtn").addEventListener("click",savePlanning);
    $("syncPlanToShoppingBtn").addEventListener("click",syncPlanToShopping);
    $("shoppingPlanningKey").addEventListener("change",()=>suggestPlanningFactor($("shoppingPlanningKey"),$("shoppingFactor")));
    $("contributionPlanningKey").addEventListener("change",()=>suggestPlanningFactor($("contributionPlanningKey"),$("contributionFactor")));
    $("lookupPriceBtn").addEventListener("click",lookupPrice);
    $("scanBarcodeBtn").addEventListener("click",startBarcodeScan);
    $("stopScanBtn").addEventListener("click",stopBarcodeScan);
    $("reloadPreviewBtn").addEventListener("click",()=>{$("sitePreview").src=`https://bodajulianycarla.bpm.red/?preview=${Date.now()}`;});
    $("instagramConnectBtn")?.addEventListener("click",connectInstagram);
    document.body.addEventListener("click",delegatedClick);
    document.body.addEventListener("change",delegatedChange);
  }

  async function api(path,opts={}){
    const o={credentials:"same-origin",...opts,headers:{...(opts.headers||{})}};
    const method=(o.method||"GET").toUpperCase();
    if(!["GET","HEAD","OPTIONS"].includes(method) && csrf) o.headers["X-CSRF-Token"]=csrf;
    if(o.body && typeof o.body!=="string"){
      o.headers["Content-Type"]="application/json";
      o.body=JSON.stringify(o.body);
    }
    const r=await fetch(path,o);
    let data={};
    try{data=await r.json();}catch(_){data={};}
    if(r.status===401 && path!=="/api/admin/login"){
      csrf=""; showLogin(); throw new Error("La sesión terminó. Ingresá nuevamente.");
    }
    if(!r.ok) throw new Error(errorText(data.error||`HTTP ${r.status}`));
    return data;
  }

  function errorText(e){
    const m={invalid_credentials:"Usuario o contraseña incorrectos.",too_many_attempts:"Demasiados intentos. Probá nuevamente en unos minutos.",unauthorized:"Sesión no válida.",name_required:"Falta el nombre.",invalid_email:"Email inválido.",description_required:"Falta el concepto.",item_required:"Falta el ítem.",title_required:"Falta el título.",negative_value:"Ese valor no puede ser negativo.",invalid_number:"Revisá el número ingresado.",invalid_seats:"Los lugares confirmados deben estar entre 0 y el cupo asignado.",invalid_seats_allowed:"La cantidad debe ser un entero positivo.",invalid_status:"Ese estado no es válido.",invalid_attendance:"La asistencia indicada no es válida.",invalid_payment_mode:"La forma de pago no es válida.",invalid_percentage:"El porcentaje debe estar entre 0 y 100.",invalid_table_capacity:"La cantidad por mesa debe estar entre 1 y 50.",invalid_guest_count:"La cantidad de personas es demasiado alta.",invalid_url:"El enlace debe empezar con https://.",invalid_coordinates:"Revisá latitud y longitud.",invalid_planning:"La configuración del planificador no es válida.",invalid_ticket:"La configuración de la tarjeta no es válida.",invalid_bank:"Los datos de transferencia no son válidos.",not_found:"No se encontró el registro."};
    return m[e]||String(e||"Ocurrió un error.");
  }

  async function login(e){
    e.preventDefault(); setLoginStatus("");
    try{
      const out=await api("/api/admin/login",{method:"POST",body:{user:$("loginUser").value.trim(),password:$("loginPassword").value}});
      csrf=out.csrf||""; $("loginPassword").value=""; showApp(); await loadState(); await loadInstagramAdminStatus();
    }catch(err){setLoginStatus(err.message);}
  }

  async function logout(){
    try{await api("/api/admin/logout",{method:"POST",body:{}});}catch(_){}
    csrf=""; showLogin();
  }

  function showLogin(){
    setViewMode("admin",false);
    $("loginView").classList.remove("hidden"); $("appView").classList.add("hidden");
  }
  function showApp(){
    $("loginView").classList.add("hidden"); $("appView").classList.remove("hidden");
    setViewMode("admin",false);
  }

  function sendCardPreviewUnlock(){
    const frame=$("fullCardPreview");
    try{frame?.contentWindow?.postMessage({type:"wedding-admin-preview"},"https://bodajulianycarla.bpm.red");}catch(_){}
  }
  function setViewMode(mode,reload=true){
    const card=mode==="card";
    $("cardView")?.classList.toggle("hidden",!card);
    $("adminShell")?.classList.toggle("hidden",card);
    $("tabs")?.classList.toggle("hidden",card);
    $("viewAdminBtn")?.classList.toggle("primary",!card);
    $("viewAdminBtn")?.classList.toggle("soft",card);
    $("viewCardBtn")?.classList.toggle("primary",card);
    $("viewCardBtn")?.classList.toggle("soft",!card);
    if(card&&reload){
      const frame=$("fullCardPreview");
      frame.src="https://bodajulianycarla.bpm.red/?admin-preview="+Date.now();
    }
  }
  function setLoginStatus(msg){const e=$("loginStatus");e.textContent=msg;e.classList.toggle("hidden",!msg);}
  function status(msg,type="ok",ms=2600){const e=$("globalStatus");e.textContent=msg;e.className=`status ${type}`;if(!msg)e.classList.add("hidden");if(msg&&ms)setTimeout(()=>{if(e.textContent===msg)e.classList.add("hidden");},ms);}

  const A11Y_NAMES={guestFilter:"Filtrar invitados",guestGroupFilter:"Filtrar por grupo",item:"Ítem",course:"Etapa del menú",unit:"Unidad",per_person:"Cantidad por persona",fixed_qty:"Cantidad fija",stock:"Stock",contributor:"Aporta",planning_key:"Categoría planificada",planning_factor:"Equivalencia por unidad",quantity:"Cantidad",estimated_value:"Valor estimado",description:"Concepto",vendor:"Proveedor",budget:"Presupuesto",actual:"Costo real",paid:"Pagado",due_date:"Fecha límite",status:"Estado",barcode:"Código de barras",needed:"Necesario",bought:"Comprado",unit_cost:"Costo por unidad",reference_price:"Precio de referencia",source:"Fuente",notes:"Notas",title:"Título",category:"Categoría",priority:"Prioridad",owner:"Responsable",name:"Nombre",contact:"Contacto",payment_mode:"Forma de pago",total:"Total"};
  function ensureAccessibleNames(root=document){
    root.querySelectorAll('input:not([type="hidden"]),select,textarea').forEach(el=>{
      if(el.getAttribute("aria-label")||el.getAttribute("aria-labelledby")||(el.labels&&el.labels.length)) return;
      let label=""; const parent=el.parentElement, local=parent?.querySelector("label");
      if(local) label=local.textContent||"";
      const key=el.dataset.edit||el.name||el.dataset.plan||el.id;
      if(!label) label=A11Y_NAMES[key]||el.placeholder||key||"Campo editable";
      label=String(label).replace(/\s+/g," ").trim();
      if(label) el.setAttribute("aria-label",label);
    });
  }

  async function loadState(){
    try{
      state=await api("/api/admin/state");
      renderAll(); ensureAccessibleNames(); $("lastUpdated").textContent=`Actualizado ${new Date().toLocaleTimeString("es-AR",{hour:"2-digit",minute:"2-digit"})}`;
    }catch(err){status(err.message,"err",5000);}
  }

  async function loadInstagramAdminStatus(){
    const el=$("instagramAdminStatus"),btn=$("instagramConnectBtn"); if(!el||!btn)return;
    try{
      const out=await api("/api/admin/instagram/status");
      if(out.connected){el.textContent=`Conectado a @${out.username||out.target_username}${out.page_name?` · Página: ${out.page_name}`:""}.`;btn.textContent="Reconectar con Meta";btn.disabled=false;}
      else if(out.configured){el.textContent=`Listo para autorizar @${out.target_username} con tu cuenta de Meta.`;btn.textContent="Conectar Instagram con Meta";btn.disabled=false;}
      else if(out.app_created){el.textContent=`Meta ya está preparada para @${out.target_username}. Falta completar la autorización segura de la cuenta.`;btn.textContent="Conectar Instagram con Meta";btn.disabled=true;}else{el.textContent=`Cuenta objetivo: @${out.target_username}. La App de Meta todavía no está configurada.`;btn.textContent="Conectar Instagram con Meta";btn.disabled=true;}
    }catch(err){el.textContent=err.message;btn.disabled=true;}
  }

  async function connectInstagram(){
    const btn=$("instagramConnectBtn"); if(!btn)return; btn.disabled=true;
    try{const out=await api("/api/admin/instagram/connect"); if(out.url)window.location.href=out.url; else throw new Error("No se recibió la URL de Meta.");}
    catch(err){status(err.message,"err",6000);btn.disabled=false;}
  }

  function openTab(name){
    document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x.dataset.tab===name));
    document.querySelectorAll(".panel").forEach(x=>x.classList.toggle("active",x.dataset.panel===name));
  }

  function renderAll(){renderDashboard();renderGuestGroupOptions();renderRsvpReviews();renderGuests();renderPlanner();renderExpenses();renderShopping();renderTasks();renderVendors();fillSettings();}
  const money=n=>new Intl.NumberFormat("es-AR",{style:"currency",currency:"ARS",maximumFractionDigits:0}).format(Number(n)||0);
  const num=n=>new Intl.NumberFormat("es-AR",{maximumFractionDigits:2}).format(Number(n)||0);
  const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const attr=esc;

  function whatsappPhone(phone){
    let digits=String(phone||"").replace(/\D/g,"");
    if(!digits)return "";
    if(digits.startsWith("00"))digits=digits.slice(2);
    if(digits.startsWith("549"))return digits;
    if(digits.startsWith("54"))return `549${digits.slice(2)}`;
    if(digits.length===10)return `549${digits}`;
    return digits;
  }

  function openWhatsApp(phone){
    const normalized=whatsappPhone(phone); if(!normalized)return;
    const fallback=`https://wa.me/${normalized}`;
    const ua=navigator.userAgent||"";
    if(!/Android|iPhone|iPad|iPod/i.test(ua)){window.open(fallback,"_blank","noopener");return;}
    const isAndroid=/Android/i.test(ua);
    const businessUrl=isAndroid
      ? `intent://send?phone=${normalized}#Intent;scheme=whatsapp;package=com.whatsapp.w4b;end`
      : `whatsapp-business://send?phone=${normalized}`;
    let leftPage=false;
    const onVisibility=()=>{if(document.visibilityState==="hidden")leftPage=true;};
    document.addEventListener("visibilitychange",onVisibility);
    window.location.href=businessUrl;
    setTimeout(()=>{
      document.removeEventListener("visibilitychange",onVisibility);
      if(!leftPage&&document.visibilityState!=="hidden")window.location.href=fallback;
    },1200);
  }

  function renderDashboard(){
    const d=state.dashboard||{};
    const cards=[
      ["Invitados",d.guests_total||0,"personas en la lista"],
      ["Confirmados",d.confirmed||0,`${d.seats||0} cubiertos`],
      ["Pendientes",d.pending||0,"por responder"],
      ["RSVP por revisar",d.rsvp_review_pending||0,"requieren identificar a la persona"],
      ["No asisten",d.declined||0,"avisaron que no"],
      ["Tarjetas cobradas",money(d.ticket_paid),`de ${money(d.ticket_expected)}`],
      ["Gastos reales",money(d.expenses_actual),`${money(d.expenses_paid)} pagados`]
    ];
    $("kpis").innerHTML=cards.map(x=>`<article class="kpi"><div class="eyebrow">${esc(x[0])}</div><strong>${esc(x[1])}</strong><span>${esc(x[2])}</span></article>`).join("");
    $("ticketSummary").innerHTML=`<div class="bigline"><strong>${money(d.ticket_paid)}</strong><span>cobrado</span></div><p class="muted">Falta registrar ${money(d.ticket_pending)} sobre ${money(d.ticket_expected)} esperados.</p>`;
    $("expenseSummary").innerHTML=`<div class="bigline"><strong>${money(d.expenses_actual)}</strong><span>real</span></div><p class="muted">Pagado ${money(d.expenses_paid)} · pendiente ${money(Math.max(0,(d.expenses_actual||0)-(d.expenses_paid||0)))}</p>`;
    const tasks=(state.tasks||[]).filter(t=>t.status!=="done");
    const upcoming=[...tasks].sort((a,b)=>(a.due_date||"9999").localeCompare(b.due_date||"9999")).slice(0,5);
    $("taskSummary").innerHTML=upcoming.length?`<ul class="mini-list">${upcoming.map(t=>`<li><b>${esc(t.title)}</b><span>${esc(t.due_date||"sin fecha")}</span></li>`).join("")}</ul>`:`<p class="muted">No hay tareas pendientes.</p>`;
    $("giftSummary").innerHTML=`<div class="bigline"><strong>${money(d.gifts)}</strong><span>aportes registrados</span></div><p class="muted">Se registran aparte de la tarjeta para que el precio de la cena no se mezcle con los regalos.</p>`;
  }

  function renderPlanner(){
    const p=state.planner||{},cfg=state.settings?.planning||{};
    const cards=[["Confirmados",p.confirmed||0,"lugares confirmados"],["A confirmar",p.invited_capacity||0,"incluidos en la previsión"],["Para planificar",p.planned||0,"confirmados + invitados + margen"],["Mesas",p.tables||0,`${p.table_capacity||10} personas c/u`],["Bebedores",p.drinkers||0,"estimación editable"]];
    $("plannerKpis").innerHTML=cards.map(x=>`<article class="kpi"><div class="eyebrow">${esc(x[0])}</div><strong>${esc(x[1])}</strong><span>${esc(x[2])}</span></article>`).join("");
    $("planningInputs").innerHTML=PLAN_FIELDS.map(([key,label,step])=>`<div><label>${esc(label)}</label><input class="field" data-plan="${attr(key)}" type="number" min="0" step="${step}" value="${attr(cfg[key]??0)}"></div>`).join("");
    $("drinkPlan").innerHTML=(p.suggestions||[]).map(x=>`<div class="plan-row"><span><b>${esc(x.label)}</b><small>${num(x.stock)} ${esc(x.unit)} en stock</small></span><span class="plan-target">${num(x.target)} ${esc(x.unit)}</span><span class="${x.missing>0?'warn':'good'}">${x.missing>0?`faltan ${num(x.missing)}`:'cubierto'}</span></div>`).join("")||'<p class="muted">Agregá confirmados o invitados para obtener el cálculo.</p>';
    $("menuPlan").innerHTML=(p.menu||[]).map(x=>x.id?`<div class="plan-row editable-plan" data-row="menu" data-id="${attr(x.id)}"><span><b>${esc(x.item)}</b><small>${esc(x.course||'')}</small></span><span>${num(x.target)} ${esc(x.unit||'')}</span><span>${editInlineNum('stock',x.stock,.01)} <small>stock</small></span><span class="${x.missing>0?'warn':'good'}">${x.missing>0?`faltan ${num(x.missing)}`:'cubierto'}</span><button class="link danger-text" data-action="delete" data-table="menu" data-id="${attr(x.id)}">Borrar</button></div>`:`<div class="plan-row"><span><b>${esc(x.item)}</b></span><span>${num(x.target)} ${esc(x.unit||'')}</span><span class="warn">base sugerida</span></div>`).join('');
    $("contributionRows").innerHTML=(state.contributions||[]).map(x=>`<div class="plan-row editable-plan" data-row="contributions" data-id="${attr(x.id)}"><span><b>${esc(x.contributor)}</b><small>${esc(x.item)}</small></span><span>${num(x.quantity)} ${esc(x.unit||'')}</span><span>${money(x.estimated_value)}</span><select class="cell-input" data-edit="status"><option value="promised" ${x.status==='promised'?'selected':''}>Prometido</option><option value="received" ${x.status==='received'?'selected':''}>Recibido</option></select><button class="link danger-text" data-action="delete" data-table="contributions" data-id="${attr(x.id)}">Borrar</button></div>`).join('')||'<p class="muted">Todavía no hay aportes cargados.</p>';
  }
  function editInlineNum(k,v,step=1){return `<input class="cell-input num mini-num" data-edit="${attr(k)}" type="number" min="0" step="${step}" value="${attr(v??0)}">`;}

  function guestUnit(g){const p=Number(state.settings?.ticket?.price)||0;return g.ticket_exempt?0:(g.ticket_override===null||g.ticket_override===undefined?p:Number(g.ticket_override)||0);}
  function guestDue(g){return Math.max(0,guestUnit(g)*Math.max(1,Number(g.seats)||1)-(Number(g.ticket_credit)||0));}
  function statusLabel(s){return ({possible:"Posible",invited:"Invitado",pending:"Pendiente",confirmed:"Confirmado",declined:"No asiste"})[s]||s||"Pendiente";}
  function guestGroupNames(){
    return [...new Set((state.guests||[]).map(g=>(g.group_name||"").trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"es",{sensitivity:"base"}));
  }
  function renderGuestGroupOptions(){
    const groups=guestGroupNames(),filter=$("guestGroupFilter"),current=filter.value;
    filter.innerHTML='<option value="">Todos los grupos</option>'+groups.map(g=>`<option value="${attr(g)}">${esc(g)}</option>`).join("")+'<option value="__ungrouped__">Sin grupo</option>';
    if([...filter.options].some(o=>o.value===current)) filter.value=current;
    $("guestGroups").innerHTML=groups.map(g=>`<option value="${attr(g)}"></option>`).join("");
  }
  function renderRsvpReviews(){
    const card=$("rsvpReviewCard"),rowsEl=$("rsvpReviewRows"),countEl=$("rsvpReviewCount");
    if(!card||!rowsEl||!countEl)return;
    const pending=(state.rsvp_submissions||[]).filter(x=>x.status==="pending");
    countEl.textContent=String(pending.length);
    card.classList.toggle("hidden",pending.length===0);
    if(!pending.length){rowsEl.innerHTML="";return;}
    const guests=[...(state.guests||[])].sort((a,b)=>String(a.name||"").localeCompare(String(b.name||""),"es",{sensitivity:"base"}));
    rowsEl.innerHTML=pending.map(r=>{
      const top=(r.candidates||[])[0]||null;
      const action=r.attendance==="yes"?"confirmó que viene":"avisó que no viene";
      const places=r.attendance==="yes"?` · ${Number(r.seats)||1} lugar${Number(r.seats)===1?"":"es"}`:"";
      const contact=[r.reported_phone,r.reported_email].filter(Boolean).map(esc).join(" · ");
      const when=r.submitted_at?new Date(r.submitted_at).toLocaleString("es-AR",{dateStyle:"short",timeStyle:"short"}):"";
      const topHtml=top?`<div class="rsvp-suggestion"><div><span class="eyebrow">¿Es este?</span><strong>${esc(top.name)}</strong><small>${esc(top.group_name||"Sin grupo")} · ${esc(top.reason)} · ${esc(top.score)}%</small></div><button class="btn primary" type="button" data-action="rsvp-match" data-submission="${attr(r.id)}" data-guest="${attr(top.guest_id)}">Sí, es este</button></div>`:`<div class="rsvp-no-match">No encontré una coincidencia suficientemente útil en la lista.</div>`;
      const options=guests.map(g=>`<option value="${attr(g.id)}">${esc(g.name)}${g.group_name?` · ${esc(g.group_name)}`:""}</option>`).join("");
      return `<article class="rsvp-review-item">
        <div class="rsvp-reported"><div><span class="eyebrow">Nombre escrito por la persona</span><h4>${esc(r.reported_name)}</h4><p><b>${esc(action)}</b>${esc(places)}${contact?` · ${contact}`:""}${when?` · ${esc(when)}`:""}</p></div><span class="pill ${r.attendance==="yes"?"confirmed":"declined"}">${r.attendance==="yes"?"Confirmó":"No asiste"}</span></div>
        ${topHtml}
        <div class="rsvp-other"><select class="field" id="rsvp-select-${attr(r.id)}"><option value="">Elegir otro invitado…</option>${options}</select><button class="btn soft" type="button" data-action="rsvp-match-selected" data-submission="${attr(r.id)}">Vincular elegido</button><button class="btn soft" type="button" data-action="rsvp-new" data-submission="${attr(r.id)}">Establecer como invitado nuevo</button></div>
      </article>`;
    }).join("");
  }

  function renderGuests(){
    const q=$("guestSearch").value.trim().toLowerCase(),f=$("guestFilter").value,gf=$("guestGroupFilter").value;
    const rows=(state.guests||[]).filter(g=>{
      const group=(g.group_name||"").trim();
      const groupOk=!gf||(gf==="__ungrouped__"?!group:group===gf);
      const searchOk=!q||[g.name,group,g.phone,g.email,g.notes,g.song,g.table_no].join(" ").toLowerCase().includes(q);
      return (!f||g.status===f)&&groupOk&&searchOk;
    }).sort((a,b)=>{
      const ga=(a.group_name||"").trim(),gb=(b.group_name||"").trim();
      if(!ga&&gb)return 1;if(ga&&!gb)return -1;
      return ga.localeCompare(gb,"es",{sensitivity:"base"})||String(a.name||"").localeCompare(String(b.name||""),"es",{sensitivity:"base"});
    });
    if(!rows.length){$("guestRows").innerHTML='<tr><td colspan="11" class="empty">No hay invitados que coincidan.</td></tr>';return;}
    const counts=new Map(); rows.forEach(g=>{const k=(g.group_name||"").trim()||"Sin grupo";counts.set(k,(counts.get(k)||0)+1);});
    let last="",html="";
    rows.forEach(g=>{
      const group=(g.group_name||"").trim()||"Sin grupo",due=guestDue(g),paid=Number(g.ticket_paid)||0;
      if(group!==last){html+=`<tr class="guest-group-row"><td colspan="11"><strong>${esc(group)}</strong><span>${counts.get(group)} invitado${counts.get(group)===1?"":"s"}</span></td></tr>`;last=group;}
      html+=`<tr>
        <td><strong>${esc(g.name)}</strong>${g.diet?`<small>🍽 ${esc(g.diet)}</small>`:""}</td>
        <td><span class="group-pill">${esc(group)}</span></td>
        <td><span class="pill ${attr(g.status)}">${esc(statusLabel(g.status))}</span></td>
        <td>${g.status==="declined"?"—":`${esc(g.seats||0)} / ${esc(g.seats_allowed||1)}`}</td>
        <td class="guest-contact">${g.phone?`<span>${esc(g.phone)}</span><a class="link whatsapp-link" data-action="whatsapp" data-phone="${attr(g.phone)}" href="https://wa.me/${attr(whatsappPhone(g.phone))}" aria-label="Escribir por WhatsApp a ${attr(g.name)}">WhatsApp</a>`:""}${g.email?`<small>${esc(g.email)}</small>`:""}</td>
        <td>${g.ticket_exempt?"Sin cargo":money(due)}${g.ticket_override!==null&&g.ticket_override!==undefined&&!g.ticket_exempt?`<small>especial ${money(g.ticket_override)} c/u</small>`:""}${g.ticket_credit?`<small class="good">aporte reconocido ${money(g.ticket_credit)}</small>`:""}</td>
        <td>${money(paid)}${due>paid?`<small class="warn">faltan ${money(due-paid)}</small>`:"<small class='good'>cubierto</small>"}</td>
        <td>${g.gift_amount?money(g.gift_amount):"—"}</td><td>${esc(g.table_no||"—")}</td>
        <td class="notes-cell">${esc(g.contribution_note||g.notes||g.gift_note||"—")}</td>
        <td class="actions"><button class="link" data-action="edit-guest" data-id="${attr(g.id)}">Editar</button><button class="link danger-text" data-action="delete" data-table="guests" data-id="${attr(g.id)}">Borrar</button></td>
      </tr>`;
    });
    $("guestRows").innerHTML=html;
  }

  function openGuest(g=null){
    $("guestModalTitle").textContent=g?"Editar invitado":"Nuevo invitado";
    $("guestId").value=g?.id||""; $("gName").value=g?.name||""; $("gGroup").value=g?.group_name||""; $("gStatus").value=g?.status||"invited";
    $("gPhone").value=g?.phone||""; $("gEmail").value=g?.email||""; $("gAttendance").value=g?.attendance||"";
    $("gSeatsAllowed").value=g?.seats_allowed??1; $("gSeats").value=g?.seats??0; $("gTicketPaid").value=g?.ticket_paid||""; $("gTicketCredit").value=g?.ticket_credit||""; $("gGiftAmount").value=g?.gift_amount||"";
    $("gContributionNote").value=g?.contribution_note||""; $("gTableNo").value=g?.table_no||""; $("gDiet").value=g?.diet||""; $("gSong").value=g?.song||"";
    $("gNotes").value=g?.notes||""; $("gGiftNote").value=g?.gift_note||"";
    if(g?.ticket_exempt) $("gTicketMode").value="free";
    else if(g?.ticket_override!==null&&g?.ticket_override!==undefined) $("gTicketMode").value="custom";
    else $("gTicketMode").value="normal";
    $("gTicketOverride").value=g?.ticket_override??""; syncTicketMode(); $("guestModal").classList.remove("hidden"); $("gName").focus();
  }
  function closeGuest(){$("guestModal").classList.add("hidden");}
  function syncTicketMode(){const custom=$("gTicketMode").value==="custom";$("gTicketOverride").disabled=!custom; if(!custom)$("gTicketOverride").value="";}
  async function saveGuest(e){
    e.preventDefault(); const id=$("guestId").value,mode=$("gTicketMode").value;
    const body={name:$("gName").value.trim(),group_name:$("gGroup").value.trim(),status:$("gStatus").value,phone:$("gPhone").value.trim(),email:$("gEmail").value.trim().toLowerCase(),attendance:$("gAttendance").value,seats:Number($("gSeats").value)||0,seats_allowed:Math.max(1,Number($("gSeatsAllowed").value)||1),ticket_exempt:mode==="free"?1:0,ticket_override:mode==="custom"?(Number($("gTicketOverride").value)||0):null,ticket_paid:Number($("gTicketPaid").value)||0,ticket_credit:Number($("gTicketCredit").value)||0,gift_amount:Number($("gGiftAmount").value)||0,contribution_note:$("gContributionNote").value.trim(),table_no:$("gTableNo").value.trim(),diet:$("gDiet").value.trim(),song:$("gSong").value.trim(),notes:$("gNotes").value.trim(),gift_note:$("gGiftNote").value.trim()};
    try{await api(id?`/api/admin/guests/${encodeURIComponent(id)}`:"/api/admin/guests",{method:id?"PATCH":"POST",body});closeGuest();await loadState();status("Invitado guardado.");}catch(err){status(err.message,"err",5000);}
  }

  function renderExpenses(){
    $("expenseRows").innerHTML=(state.expenses||[]).length?state.expenses.map(x=>`<tr data-row="expenses" data-id="${attr(x.id)}">
      ${editCell("description",x.description)}${editCell("category",x.category)}${editCell("vendor",x.vendor)}${editNum("budget",x.budget)}${editNum("actual",x.actual)}${editNum("paid",x.paid)}
      <td>${money(Math.max(0,(Number(x.actual)||0)-(Number(x.paid)||0)))}</td>${editDate("due_date",x.due_date)}<td class="actions"><button class="link danger-text" data-action="delete" data-table="expenses" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="9" class="empty">Todavía no hay gastos cargados.</td></tr>`;
  }
  function renderShopping(){
    const label={water:"Agua",soft:"Gaseosa/mixer",beer:"Cerveza",wine:"Vino",sparkling:"Espumante",spirits:"Destilado",ice:"Hielo"};
    $("shoppingRows").innerHTML=(state.shopping||[]).length?state.shopping.map(x=>`<tr data-row="shopping" data-id="${attr(x.id)}">
      ${editCell("item",x.item)}<td>${esc(label[x.planning_key]||x.category||"—")}${x.barcode?`<small>${esc(x.barcode)}</small>`:""}</td>${editCell("unit",x.unit)}${editNum("needed",x.needed,.01)}${editNum("bought",x.bought,.01)}<td>${num(Math.max(0,(Number(x.needed)||0)-(Number(x.bought)||0)))}</td>${editNum("unit_cost",x.unit_cost,.01)}${editNum("reference_price",x.reference_price,.01)}<td>${esc(x.source||"—")}</td><td class="actions"><button class="link" data-action="lookup-row" data-id="${attr(x.id)}">Precio</button><button class="link danger-text" data-action="delete" data-table="shopping" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="10" class="empty">Todavía no hay stock o compras cargadas.</td></tr>`;
  }
  function renderTasks(){
    $("taskRows").innerHTML=(state.tasks||[]).length?state.tasks.map(x=>`<tr data-row="tasks" data-id="${attr(x.id)}">${editCell("title",x.title)}${editCell("category",x.category)}${editDate("due_date",x.due_date)}<td><select class="cell-input" data-edit="priority"><option value="low" ${x.priority==="low"?"selected":""}>Baja</option><option value="normal" ${x.priority==="normal"?"selected":""}>Normal</option><option value="high" ${x.priority==="high"?"selected":""}>Alta</option></select></td>${editCell("owner",x.owner)}<td><select class="cell-input" data-edit="status"><option value="pending" ${x.status==="pending"?"selected":""}>Pendiente</option><option value="doing" ${x.status==="doing"?"selected":""}>En curso</option><option value="done" ${x.status==="done"?"selected":""}>Lista</option></select></td><td class="actions"><button class="link danger-text" data-action="delete" data-table="tasks" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="7" class="empty">No hay tareas cargadas.</td></tr>`;
  }
  function renderVendors(){
    const pay={cash:"Dinero",contribution:"Aporte/canje",mixed:"Mixto",free:"Sin cargo"};
    $("vendorRows").innerHTML=(state.vendors||[]).length?state.vendors.map(x=>`<tr data-row="vendors" data-id="${attr(x.id)}">${editCell("category",x.category)}${editCell("name",x.name)}${editCell("role",x.role)}<td>${esc(pay[x.payment_mode]||x.payment_mode||"Dinero")}</td>${editNum("total",x.total)}${editNum("paid",x.paid)}<td>${money(Math.max(0,(Number(x.total)||0)-(Number(x.paid)||0)))}</td>${editCell("contribution_note",x.contribution_note)}<td class="actions"><button class="link danger-text" data-action="delete" data-table="vendors" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="9" class="empty">No hay personas o proveedores cargados.</td></tr>`;
  }
  function editCell(k,v){return `<td><input class="cell-input" data-edit="${attr(k)}" value="${attr(v||"")}"></td>`;}
  function editNum(k,v,step=1){return `<td><input class="cell-input num" data-edit="${attr(k)}" type="number" min="0" step="${step}" value="${attr(v??0)}"></td>`;}
  function editDate(k,v){return `<td><input class="cell-input" data-edit="${attr(k)}" type="date" value="${attr(v||"")}"></td>`;}

  async function createFromForm(e,table){
    e.preventDefault(); const form=e.currentTarget, fd=new FormData(form),body={};
    for(const [k,v] of fd) body[k]=v;
    for(const k of ["budget","actual","paid","needed","bought","unit_cost","total","reference_price","planning_factor","per_person","fixed_qty","stock","quantity","estimated_value"]) if(k in body)body[k]=Number(body[k])||0;
    if(table==="contributions")body.status="promised";
    try{await api(`/api/admin/${table}`,{method:"POST",body});form.reset();await loadState();status("Agregado.");}catch(err){status(err.message,"err",5000);}
  }

  async function seedWeddingTasks(){
    const base=[
      ["Invitados","Cerrar lista inicial de invitados"],["Invitados","Revisar confirmaciones y pendientes"],["Ceremonia","Confirmar ceremonia, horario y documentación"],
      ["Comida","Definir menú y restricciones alimentarias"],["Bebidas","Calcular y comprar bebidas, hielo y agua"],["Fiesta","Confirmar DJ, sonido y música clave"],
      ["Foto & video","Confirmar fotografía y video"],["Ambientación","Definir decoración, flores e iluminación"],["Salón","Confirmar mesas, sillas, vajilla y mantelería"],
      ["Equipo","Confirmar mozos / barra / responsables"],["Torta","Definir torta y mesa dulce"],["Logística","Plan de llegada, estacionamiento y traslados"],
      ["Pagos","Revisar señas, saldos y vencimientos de proveedores"],["Novios","Anillos, ropa y accesorios"],["Final","Armar cronograma del día y contactos de emergencia"]
    ];
    if((state.tasks||[]).length && !confirm("Ya hay tareas cargadas. ¿Querés sumar igualmente el checklist base?"))return;
    try{
      for(const [category,title] of base) await api("/api/admin/tasks",{method:"POST",body:{category,title,priority:"normal",status:"pending"}});
      await loadState(); status("Checklist base agregado.");
    }catch(err){status(err.message,"err",5000);}
  }

  async function resolveRsvp(submissionId,action,guestId=""){
    const body={action};if(guestId)body.guest_id=guestId;
    try{
      await api(`/api/admin/rsvp-submissions/${encodeURIComponent(submissionId)}/resolve`,{method:"POST",body});
      await loadState();openTab("guests");
      status(action==="new"?"Se creó el invitado nuevo y se aplicó su respuesta.":"Respuesta vinculada al invitado de la lista.");
    }catch(err){status(err.message,"err",6000);}
  }

  async function delegatedClick(e){
    const layoutButton=e.target.closest("[data-layout-action]");
    if(layoutButton){
      const row=layoutButton.closest(".layout-row"),direction=layoutButton.dataset.layoutAction,target=direction==="up"?row?.previousElementSibling:row?.nextElementSibling;
      if(row&&target){row.parentElement.insertBefore(target,direction==="up"?row:target);refreshLayoutOrder();}
      return;
    }
    const b=e.target.closest("[data-action]"); if(!b)return;
    if(b.dataset.action==="rsvp-match"){await resolveRsvp(b.dataset.submission,"match",b.dataset.guest);return;}
    if(b.dataset.action==="rsvp-match-selected"){
      const select=$(`rsvp-select-${b.dataset.submission}`),guestId=select?.value||"";
      if(!guestId){status("Elegí un invitado de la lista.","err",4000);return;}
      await resolveRsvp(b.dataset.submission,"match",guestId);return;
    }
    if(b.dataset.action==="rsvp-new"){
      const item=(state.rsvp_submissions||[]).find(x=>x.id===b.dataset.submission);
      if(item&&!confirm(`¿Crear a "${item.reported_name}" como invitado nuevo y aplicar esta respuesta?`))return;
      await resolveRsvp(b.dataset.submission,"new");return;
    }
    if(b.dataset.action==="whatsapp"){e.preventDefault();openWhatsApp(b.dataset.phone);return;}
    if(b.dataset.action==="edit-guest"){const g=(state.guests||[]).find(x=>x.id===b.dataset.id);if(g)openGuest(g);return;}
    if(b.dataset.action==="lookup-row"){const x=(state.shopping||[]).find(v=>v.id===b.dataset.id);if(x?.barcode)await lookupPrice(x);else status("Ese producto no tiene código de barras.","err");return;}
    if(b.dataset.action==="delete"){
      const label=b.dataset.table==="guests"?"este invitado":"este registro";
      if(!confirm(`¿Borrar ${label}?`))return;
      try{await api(`/api/admin/${b.dataset.table}/${encodeURIComponent(b.dataset.id)}`,{method:"DELETE",body:{}});await loadState();status("Eliminado.");}catch(err){status(err.message,"err",5000);}
    }
  }
  async function delegatedChange(e){
    const input=e.target.closest("[data-edit]");if(!input)return;
    const row=input.closest("[data-row]");if(!row)return;
    const table=row.dataset.row,id=row.dataset.id,field=input.dataset.edit;
    let value=input.type==="checkbox"?(input.checked?1:0):input.value;
    if(input.type==="number")value=Number(value)||0;
    input.disabled=true;
    try{await api(`/api/admin/${table}/${encodeURIComponent(id)}`,{method:"PATCH",body:{[field]:value}});await loadState();}
    catch(err){status(err.message,"err",5000);await loadState();}
  }

  function fillSettings(){
    const s=state.settings||{},t=s.ticket||{},b=s.bank||{},c=s.ceremony||{},f=s.celebration||{},d=s.dress||{},copy=s.copy||{};
    $("copyFields").innerHTML=COPY_FIELDS.map(([key,label])=>`<div class="copy-field"><label>${esc(label)}</label><textarea class="field" data-copy-key="${attr(key)}" rows="2">${esc(copy[key]||"")}</textarea></div>`).join("");
    renderLayout(s.layout);
    $("ticketEnabled").checked=t.enabled!==false; $("ticketPriceInput").value=t.price??0; $("ticketTextInput").value=t.text||"";
    $("bankHolderInput").value=b.holder||""; $("bankAliasInput").value=b.alias||""; $("bankCbuInput").value=b.cbu||""; $("bankMpInput").value=b.mp_url||"";
    $("ceremonyTimeInput").value=c.time||""; $("ceremonyTitleInput").value=c.title||""; $("ceremonyPlaceInput").value=c.place||""; $("ceremonyAddressInput").value=c.address||""; $("ceremonyLatInput").value=c.lat??""; $("ceremonyLngInput").value=c.lng??"";
    $("celebrationTimeInput").value=f.time||""; $("celebrationTitleInput").value=f.title||""; $("celebrationPlaceInput").value=f.place||""; $("celebrationAddressInput").value=f.address||""; $("celebrationLatInput").value=f.lat??""; $("celebrationLngInput").value=f.lng??"";
    $("dressTitleInput").value=d.title||""; $("dressConceptInput").value=d.concept||""; $("dressDetailsInput").value=d.details||"";
    $("deadlineInput").value=s.rsvp_deadline_display||""; $("fallbackWaInput").value=s.fallback_whatsapp||"";
  }

  function normalizedLayout(layout){
    const configured=Array.isArray(layout?.sections)?layout.sections:[],seen=new Set(),out=[];
    configured.forEach(x=>{
      if(!LAYOUT_DEFAULTS.some(([id])=>id===x.id)||seen.has(x.id))return;
      seen.add(x.id);out.push({id:x.id,label:x.label||LAYOUT_DEFAULTS.find(([id])=>id===x.id)[1],visible:x.visible!==false});
    });
    LAYOUT_DEFAULTS.forEach(([id,label])=>{if(!seen.has(id))out.push({id,label,visible:true});});
    return out;
  }

  function renderLayout(layout){
    const el=$("layoutFields"); if(!el)return;
    const rows=normalizedLayout(layout);
    el.innerHTML=rows.map((x,i)=>`<div class="layout-row" draggable="true" data-layout-id="${attr(x.id)}"><label class="layout-visible"><input type="checkbox" data-layout-visible ${x.visible?"checked":""}> <span>${esc(x.label)}</span></label><span class="layout-order">${i+1}</span><button class="link" type="button" data-layout-action="up" ${i===0?"disabled":""}>Subir</button><button class="link" type="button" data-layout-action="down" ${i===rows.length-1?"disabled":""}>Bajar</button></div>`).join("");
    let dragged=null;
    el.querySelectorAll(".layout-row").forEach(row=>{
      row.addEventListener("dragstart",()=>{dragged=row;row.classList.add("dragging");});
      row.addEventListener("dragend",()=>{row.classList.remove("dragging");dragged=null;refreshLayoutOrder();});
      row.addEventListener("dragover",event=>{event.preventDefault();if(dragged&&dragged!==row){const box=row.getBoundingClientRect(),after=event.clientY>box.top+box.height/2;el.insertBefore(dragged,after?row.nextSibling:row);refreshLayoutOrder();}});
    });
  }

  function readLayout(){
    return {sections:[...document.querySelectorAll("#layoutFields .layout-row")].map(row=>({id:row.dataset.layoutId,label:row.querySelector(".layout-visible span")?.textContent||row.dataset.layoutId,visible:row.querySelector("[data-layout-visible]")?.checked!==false}))};
  }

  function refreshLayoutOrder(){
    const rows=[...document.querySelectorAll("#layoutFields .layout-row")];
    rows.forEach((row,i)=>{row.querySelector(".layout-order").textContent=i+1;row.querySelector('[data-layout-action="up"]').disabled=i===0;row.querySelector('[data-layout-action="down"]').disabled=i===rows.length-1;});
  }

  async function saveSettings(){
    const old=state.settings||{},copy={};
    const numOr=(id,fallback)=>{const raw=$(id).value.trim();if(raw==="")return Number(fallback);const n=Number(raw);return Number.isFinite(n)?n:Number(fallback);};
    document.querySelectorAll("[data-copy-key]").forEach(x=>copy[x.dataset.copyKey]=x.value.trim());
    const settings={...old,copy,layout:readLayout(),
      rsvp_deadline_display:$("deadlineInput").value.trim(),fallback_whatsapp:$("fallbackWaInput").value.replace(/\D/g,""),
      ticket:{...(old.ticket||{}),enabled:$("ticketEnabled").checked,price:Number($("ticketPriceInput").value)||0,currency:"ARS",text:$("ticketTextInput").value.trim()},
      bank:{holder:$("bankHolderInput").value.trim(),alias:$("bankAliasInput").value.trim(),cbu:$("bankCbuInput").value.replace(/\s/g,""),mp_url:$("bankMpInput").value.trim()},
      ceremony:{...(old.ceremony||{}),time:$("ceremonyTimeInput").value.trim(),title:$("ceremonyTitleInput").value.trim(),place:$("ceremonyPlaceInput").value.trim(),address:$("ceremonyAddressInput").value.trim(),lat:numOr("ceremonyLatInput",old.ceremony?.lat),lng:numOr("ceremonyLngInput",old.ceremony?.lng)},
      celebration:{...(old.celebration||{}),time:$("celebrationTimeInput").value.trim(),title:$("celebrationTitleInput").value.trim(),place:$("celebrationPlaceInput").value.trim(),address:$("celebrationAddressInput").value.trim(),lat:numOr("celebrationLatInput",old.celebration?.lat),lng:numOr("celebrationLngInput",old.celebration?.lng)},
      dress:{title:$("dressTitleInput").value.trim(),concept:$("dressConceptInput").value.trim(),details:$("dressDetailsInput").value.trim()}
    };
    try{await api("/api/admin/settings",{method:"PUT",body:settings});await loadState();$("sitePreview").src=`https://bodajulianycarla.bpm.red/?preview=${Date.now()}`;status("Sitio y tarjeta actualizados.");}
    catch(err){status(err.message,"err",5000);}
  }

  async function savePlanning(){
    const planning={...(state.settings?.planning||{})};
    document.querySelectorAll("[data-plan]").forEach(x=>planning[x.dataset.plan]=Number(x.value)||0);
    try{await api("/api/admin/settings",{method:"PUT",body:{planning}});await loadState();status("Planificación actualizada.");}
    catch(err){status(err.message,"err",5000);}
  }
  function suggestPlanningFactor(select,input){
    const defaults={water:1.5,soft:2.25,beer:.473,wine:.75,sparkling:.75,spirits:.75,ice:1};
    if(select.value && (!Number(input.value)||Number(input.value)===1)) input.value=defaults[select.value]||1;
  }
  async function syncPlanToShopping(){
    const suggestions=state.planner?.suggestions||[];
    try{
      for(const x of suggestions){
        const row=(state.shopping||[]).find(v=>v.planning_key===x.key),factor=Math.max(.001,Number(row?.planning_factor)||1),needed=Math.ceil((Number(x.target)||0)/factor*100)/100;
        if(row) await api(`/api/admin/shopping/${encodeURIComponent(row.id)}`,{method:"PATCH",body:{needed}});
        else await api("/api/admin/shopping",{method:"POST",body:{item:x.label,category:"Bebidas",planning_key:x.key,unit:x.unit,planning_factor:1,needed:Number(x.target)||0,bought:0}});
      }
      await loadState();openTab("shopping");status("Compras actualizadas con los objetivos del planificador.");
    }catch(err){status(err.message,"err",5000);}
  }

  function showPriceStatus(html,type="ok"){
    const el=$("priceLookupStatus");el.className=`status ${type}`;el.innerHTML=html;el.classList.remove("hidden");
  }
  async function lookupPrice(row=null){
    const barcode=(row?.barcode||$("shoppingBarcode").value||"").replace(/\D/g,"");
    if(barcode.length<8){showPriceStatus("Ingresá o escaneá un código de barras válido.","err");return;}
    showPriceStatus("Buscando precios de referencia cerca de Jujuy…","ok");
    try{
      const r=await api(`/api/admin/price-lookup?barcode=${encodeURIComponent(barcode)}`);
      const offers=r.offers||[],best=offers[0];
      if(row){
        if(best)await api(`/api/admin/shopping/${encodeURIComponent(row.id)}`,{method:"PATCH",body:{reference_price:best.price,source:r.source||"Precios Claros",source_url:r.source_url||"",reference_updated_at:new Date().toISOString()}});
        await loadState();
      }else{
        if(r.name&&!$("shoppingItem").value)$("shoppingItem").value=r.name;
        if(best)$("shoppingRefPrice").value=best.price;
        $("shoppingSource").value=r.source||"Precios Claros";
      }
      showPriceStatus(best?`Referencia encontrada: <b>${money(best.price)}</b>${best.store?` · ${esc(best.store)}`:""}. ${offers.length>1?`${offers.length} precios relevados.`:""}`:"No encontré precio vigente para ese código. Podés cargarlo manualmente.",best?"ok":"err");
    }catch(err){showPriceStatus(`No se pudo consultar la fuente de precios: ${esc(err.message)}`,"err");}
  }
  async function startBarcodeScan(){
    if(!('BarcodeDetector' in window)){showPriceStatus("Este navegador no admite escaneo directo. Podés escribir el código de barras y usar Buscar precio.","err");return;}
    try{
      scanStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"}}});
      const video=$("barcodeVideo");video.srcObject=scanStream;await video.play();$("barcodeScanner").classList.remove("hidden");
      const detector=new BarcodeDetector({formats:["ean_13","ean_8","upc_a","upc_e","code_128"]});
      scanTimer=setInterval(async()=>{try{const codes=await detector.detect(video);if(codes[0]?.rawValue){$("shoppingBarcode").value=codes[0].rawValue;stopBarcodeScan();await lookupPrice();}}catch(_){}},500);
    }catch(err){showPriceStatus("No pude abrir la cámara. Revisá el permiso del navegador o cargá el código manualmente.","err");}
  }
  function stopBarcodeScan(){if(scanTimer){clearInterval(scanTimer);scanTimer=null;}if(scanStream){scanStream.getTracks().forEach(t=>t.stop());scanStream=null;}$("barcodeScanner").classList.add("hidden");}

  async function importBackup(e){
    const file=e.target.files?.[0]; e.target.value=""; if(!file)return;
    let raw;
    try{raw=JSON.parse(await file.text());}catch(_){status("El archivo no es un JSON válido.","err",5000);return;}
    if(!confirm("Se van a SUMAR los datos del archivo a la base actual. No se borra nada. ¿Continuar?"))return;
    const jobs=[];
    const push=(table,obj)=>jobs.push(()=>api(`/api/admin/${table}`,{method:"POST",body:obj}));
    const statusMap={confirmado:"confirmed",pendiente:"pending",posible:"possible",no_asiste:"declined",invitado:"invited"};
    const places=v=>{const x=String(v||"").toLowerCase();if(x.includes("grupo"))return 4;const m=x.match(/\d+/);return m?Number(m[0]):1;};
    const src=raw.state||raw;
    for(const g of (src.guests||[])){
      push("guests",{
        name:g.name||"Invitado",group_name:g.group_name||g.group||g.grupo||"",phone:g.phone||"",email:g.email||"",
        status:statusMap[g.listStatus]||g.status||((g.attendance||"").toLowerCase().includes("no")?"declined":"pending"),
        attendance:g.attendance==="yes"||String(g.attendance||"").toLowerCase().includes("sí")||String(g.attendance||"").toLowerCase().includes("confirmo")?"yes":(g.attendance==="no"||String(g.attendance||"").toLowerCase().includes("no")?"no":""),
        seats:Number(g.seats)||places(g.places),diet:g.diet||"",song:g.song||"",notes:g.notes||"",
        ticket_override:g.ticket_override??null,ticket_exempt:Number(g.ticket_exempt)||0,ticket_paid:Number(g.ticket_paid)||0,
        gift_amount:Number(g.gift_amount)||0,gift_note:g.gift_note||"",table_no:g.table_no||""
      });
    }
    for(const x of (src.expenses||[])) push("expenses",pick(x,["category","description","vendor","budget","actual","paid","due_date","status","notes"]));
    for(const x of (src.shopping||[])) push("shopping",pick(x,["category","item","unit","needed","bought","unit_cost","done","notes"]));
    for(const x of (src.tasks||[])) push("tasks",pick(x,["title","category","due_date","priority","owner","status","notes"]));
    for(const x of (src.vendors||[])) push("vendors",{category:x.category||x.rubro||"",name:x.name||"Proveedor",contact:x.contact||"",total:Number(x.total??x.cost)||0,paid:Number(x.paid)||0,due_date:x.due_date||"",status:x.status||"pending",notes:x.notes||""});
    for(const x of (src.songs||src.pista||[])){const title=typeof x==="string"?x:(x.title||"");if(title)push("songs",{title,source:"import",active:1});}
    for(const x of (raw.checklist||[])) if(x.name) push("tasks",{title:x.name,category:"Checklist anterior",status:x.done?"done":"pending",notes:x.note||""});
    let settings=src.settings||null;
    if(!settings && raw.siteData){
      const o=raw.siteData;
      settings={...state.settings};
      if(o.ticket)settings.ticket={...settings.ticket,...o.ticket};
      if(o.bank)settings.bank={holder:o.bank.holder||"",alias:o.bank.alias||"",cbu:o.bank.cbu||"",mp_url:o.bank.mpUrl||o.bank.mp_url||""};
      if(o.ceremony)settings.ceremony={...settings.ceremony,...o.ceremony};
      if(o.celebration)settings.celebration={...settings.celebration,...o.celebration};
    }
    try{
      status(`Importando ${jobs.length} registros…`,"ok",0);
      for(let i=0;i<jobs.length;i+=6) await Promise.all(jobs.slice(i,i+6).map(fn=>fn()));
      if(settings) await api("/api/admin/settings",{method:"PUT",body:settings});
      await loadState(); status(`Importación terminada: ${jobs.length} registros sumados.`);
    }catch(err){status(`La importación se detuvo: ${err.message}`,"err",7000);}
  }
  function pick(obj,keys){const out={};for(const k of keys)if(obj[k]!==undefined)out[k]=obj[k];return out;}

  function download(name,text,type="application/json"){
    const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},0);
  }
  function downloadBackup(){download(`boda-backup-${new Date().toISOString().slice(0,10)}.json`,JSON.stringify(state,null,2));}
  function csvCell(v){return `"${String(v??"").replace(/"/g,'""')}"`;}
  function downloadGuestsCsv(){
    const head=["Nombre","Grupo","Estado","Asistencia","Lugares","Telefono","Email","TarjetaUnit","TarjetaPagada","Regalo","Mesa","Menu","Cancion","Notas"];
    const rows=(state.guests||[]).map(g=>[g.name,g.group_name||"",statusLabel(g.status),g.attendance,g.seats,g.phone,g.email,guestUnit(g),g.ticket_paid,g.gift_amount,g.table_no,g.diet,g.song,g.notes].map(csvCell).join(","));
    download("invitados-boda.csv","\ufeff"+[head.map(csvCell).join(","),...rows].join("\r\n"),"text/csv;charset=utf-8");
  }
})();
