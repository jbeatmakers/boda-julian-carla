(()=>{
  "use strict";
  const $=id=>document.getElementById(id);
  let csrf="";
  let state={settings:{},dashboard:{},guests:[],expenses:[],shopping:[],tasks:[],vendors:[],songs:[]};

  document.addEventListener("DOMContentLoaded",init);

  async function init(){
    bindStatic();
    try{
      const s=await api("/api/admin/session");
      if(s.authenticated){csrf=s.csrf||"";showApp();await loadState();}
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
    $("addGuestBtn").addEventListener("click",()=>openGuest());
    $("closeGuestModal").addEventListener("click",closeGuest);
    $("cancelGuest").addEventListener("click",closeGuest);
    $("guestModal").addEventListener("click",e=>{if(e.target===$("guestModal"))closeGuest();});
    $("guestForm").addEventListener("submit",saveGuest);
    $("gTicketMode").addEventListener("change",syncTicketMode);
    $("expenseForm").addEventListener("submit",e=>createFromForm(e,"expenses"));
    $("shoppingForm").addEventListener("submit",e=>createFromForm(e,"shopping"));
    $("taskForm").addEventListener("submit",e=>createFromForm(e,"tasks"));
    $("seedTasksBtn").addEventListener("click",seedWeddingTasks);
    $("vendorForm").addEventListener("submit",e=>createFromForm(e,"vendors"));
    $("saveSettingsBtn").addEventListener("click",saveSettings);
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
    const m={invalid_credentials:"Usuario o contraseña incorrectos.",too_many_attempts:"Demasiados intentos. Probá nuevamente en unos minutos.",unauthorized:"Sesión no válida.",name_required:"Falta el nombre.",invalid_email:"Email inválido.",description_required:"Falta el concepto.",item_required:"Falta el ítem.",title_required:"Falta el título.",not_found:"No se encontró el registro."};
    return m[e]||String(e||"Ocurrió un error.");
  }

  async function login(e){
    e.preventDefault(); setLoginStatus("");
    try{
      const out=await api("/api/admin/login",{method:"POST",body:{user:$("loginUser").value.trim(),password:$("loginPassword").value}});
      csrf=out.csrf||""; $("loginPassword").value=""; showApp(); await loadState();
    }catch(err){setLoginStatus(err.message);}
  }

  async function logout(){
    try{await api("/api/admin/logout",{method:"POST",body:{}});}catch(_){}
    csrf=""; showLogin();
  }

  function showLogin(){
    $("loginView").classList.remove("hidden"); $("appView").classList.add("hidden");
  }
  function showApp(){
    $("loginView").classList.add("hidden"); $("appView").classList.remove("hidden");
  }
  function setLoginStatus(msg){const e=$("loginStatus");e.textContent=msg;e.classList.toggle("hidden",!msg);}
  function status(msg,type="ok",ms=2600){const e=$("globalStatus");e.textContent=msg;e.className=`status ${type}`;if(!msg)e.classList.add("hidden");if(msg&&ms)setTimeout(()=>{if(e.textContent===msg)e.classList.add("hidden");},ms);}

  async function loadState(){
    try{
      state=await api("/api/admin/state");
      renderAll(); $("lastUpdated").textContent=`Actualizado ${new Date().toLocaleTimeString("es-AR",{hour:"2-digit",minute:"2-digit"})}`;
    }catch(err){status(err.message,"err",5000);}
  }

  function openTab(name){
    document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x.dataset.tab===name));
    document.querySelectorAll(".panel").forEach(x=>x.classList.toggle("active",x.dataset.panel===name));
  }

  function renderAll(){renderDashboard();renderGuests();renderExpenses();renderShopping();renderTasks();renderVendors();fillSettings();}
  const money=n=>new Intl.NumberFormat("es-AR",{style:"currency",currency:"ARS",maximumFractionDigits:0}).format(Number(n)||0);
  const num=n=>new Intl.NumberFormat("es-AR",{maximumFractionDigits:2}).format(Number(n)||0);
  const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const attr=esc;

  function renderDashboard(){
    const d=state.dashboard||{};
    const cards=[
      ["Invitados",d.guests_total||0,"personas en la lista"],
      ["Confirmados",d.confirmed||0,`${d.seats||0} cubiertos`],
      ["Pendientes",d.pending||0,"por responder"],
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

  function guestUnit(g){const p=Number(state.settings?.ticket?.price)||0;return g.ticket_exempt?0:(g.ticket_override===null||g.ticket_override===undefined?p:Number(g.ticket_override)||0);}
  function guestDue(g){return guestUnit(g)*Math.max(1,Number(g.seats)||1);}
  function statusLabel(s){return ({possible:"Posible",invited:"Invitado",pending:"Pendiente",confirmed:"Confirmado",declined:"No asiste"})[s]||s||"Pendiente";}
  function renderGuests(){
    const q=$("guestSearch").value.trim().toLowerCase(),f=$("guestFilter").value;
    const rows=(state.guests||[]).filter(g=>(!f||g.status===f)&&(!q||[g.name,g.phone,g.email,g.notes,g.song,g.table_no].join(" ").toLowerCase().includes(q)));
    $("guestRows").innerHTML=rows.length?rows.map(g=>{
      const due=guestDue(g),paid=Number(g.ticket_paid)||0;
      return `<tr>
        <td><strong>${esc(g.name)}</strong>${g.diet?`<small>🍽 ${esc(g.diet)}</small>`:""}</td>
        <td><span class="pill ${attr(g.status)}">${esc(statusLabel(g.status))}</span></td>
        <td>${g.status==="declined"?"—":esc(g.seats||1)}</td>
        <td>${g.phone?esc(g.phone):""}${g.email?`<small>${esc(g.email)}</small>`:""}</td>
        <td>${g.ticket_exempt?"Sin cargo":money(due)}${g.ticket_override!==null&&g.ticket_override!==undefined&&!g.ticket_exempt?`<small>especial ${money(g.ticket_override)} c/u</small>`:""}</td>
        <td>${money(paid)}${due>paid?`<small class="warn">faltan ${money(due-paid)}</small>`:"<small class='good'>cubierto</small>"}</td>
        <td>${g.gift_amount?money(g.gift_amount):"—"}</td><td>${esc(g.table_no||"—")}</td>
        <td class="notes-cell">${esc(g.notes||g.gift_note||"—")}</td>
        <td class="actions"><button class="link" data-action="edit-guest" data-id="${attr(g.id)}">Editar</button><button class="link danger-text" data-action="delete" data-table="guests" data-id="${attr(g.id)}">Borrar</button></td>
      </tr>`;
    }).join(""):`<tr><td colspan="10" class="empty">No hay invitados que coincidan.</td></tr>`;
  }

  function openGuest(g=null){
    $("guestModalTitle").textContent=g?"Editar invitado":"Nuevo invitado";
    $("guestId").value=g?.id||""; $("gName").value=g?.name||""; $("gStatus").value=g?.status||"invited";
    $("gPhone").value=g?.phone||""; $("gEmail").value=g?.email||""; $("gAttendance").value=g?.attendance||"";
    $("gSeats").value=g?.seats??1; $("gTicketPaid").value=g?.ticket_paid||""; $("gGiftAmount").value=g?.gift_amount||"";
    $("gTableNo").value=g?.table_no||""; $("gDiet").value=g?.diet||""; $("gSong").value=g?.song||"";
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
    const body={name:$("gName").value.trim(),status:$("gStatus").value,phone:$("gPhone").value.trim(),email:$("gEmail").value.trim().toLowerCase(),attendance:$("gAttendance").value,seats:Number($("gSeats").value)||0,ticket_exempt:mode==="free"?1:0,ticket_override:mode==="custom"?(Number($("gTicketOverride").value)||0):null,ticket_paid:Number($("gTicketPaid").value)||0,gift_amount:Number($("gGiftAmount").value)||0,table_no:$("gTableNo").value.trim(),diet:$("gDiet").value.trim(),song:$("gSong").value.trim(),notes:$("gNotes").value.trim(),gift_note:$("gGiftNote").value.trim()};
    try{await api(id?`/api/admin/guests/${encodeURIComponent(id)}`:"/api/admin/guests",{method:id?"PATCH":"POST",body});closeGuest();await loadState();status("Invitado guardado.");}catch(err){status(err.message,"err",5000);}
  }

  function renderExpenses(){
    $("expenseRows").innerHTML=(state.expenses||[]).length?state.expenses.map(x=>`<tr data-row="expenses" data-id="${attr(x.id)}">
      ${editCell("description",x.description)}${editCell("category",x.category)}${editCell("vendor",x.vendor)}${editNum("budget",x.budget)}${editNum("actual",x.actual)}${editNum("paid",x.paid)}
      <td>${money(Math.max(0,(Number(x.actual)||0)-(Number(x.paid)||0)))}</td>${editDate("due_date",x.due_date)}<td class="actions"><button class="link danger-text" data-action="delete" data-table="expenses" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="9" class="empty">Todavía no hay gastos cargados.</td></tr>`;
  }
  function renderShopping(){
    $("shoppingRows").innerHTML=(state.shopping||[]).length?state.shopping.map(x=>`<tr data-row="shopping" data-id="${attr(x.id)}">
      ${editCell("item",x.item)}${editCell("category",x.category)}${editCell("unit",x.unit)}${editNum("needed",x.needed,.01)}${editNum("bought",x.bought,.01)}<td>${num(Math.max(0,(Number(x.needed)||0)-(Number(x.bought)||0)))}</td>${editNum("unit_cost",x.unit_cost,.01)}<td><input data-edit="done" type="checkbox" ${x.done?"checked":""}></td><td class="actions"><button class="link danger-text" data-action="delete" data-table="shopping" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="9" class="empty">Todavía no hay compras cargadas.</td></tr>`;
  }
  function renderTasks(){
    $("taskRows").innerHTML=(state.tasks||[]).length?state.tasks.map(x=>`<tr data-row="tasks" data-id="${attr(x.id)}">${editCell("title",x.title)}${editCell("category",x.category)}${editDate("due_date",x.due_date)}<td><select class="cell-input" data-edit="priority"><option value="low" ${x.priority==="low"?"selected":""}>Baja</option><option value="normal" ${x.priority==="normal"?"selected":""}>Normal</option><option value="high" ${x.priority==="high"?"selected":""}>Alta</option></select></td>${editCell("owner",x.owner)}<td><select class="cell-input" data-edit="status"><option value="pending" ${x.status==="pending"?"selected":""}>Pendiente</option><option value="doing" ${x.status==="doing"?"selected":""}>En curso</option><option value="done" ${x.status==="done"?"selected":""}>Lista</option></select></td><td class="actions"><button class="link danger-text" data-action="delete" data-table="tasks" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="7" class="empty">No hay tareas cargadas.</td></tr>`;
  }
  function renderVendors(){
    $("vendorRows").innerHTML=(state.vendors||[]).length?state.vendors.map(x=>`<tr data-row="vendors" data-id="${attr(x.id)}">${editCell("category",x.category)}${editCell("name",x.name)}${editCell("contact",x.contact)}${editNum("total",x.total)}${editNum("paid",x.paid)}<td>${money(Math.max(0,(Number(x.total)||0)-(Number(x.paid)||0)))}</td>${editDate("due_date",x.due_date)}<td class="actions"><button class="link danger-text" data-action="delete" data-table="vendors" data-id="${attr(x.id)}">Borrar</button></td></tr>`).join(""):`<tr><td colspan="8" class="empty">No hay proveedores cargados.</td></tr>`;
  }
  function editCell(k,v){return `<td><input class="cell-input" data-edit="${attr(k)}" value="${attr(v||"")}"></td>`;}
  function editNum(k,v,step=1){return `<td><input class="cell-input num" data-edit="${attr(k)}" type="number" min="0" step="${step}" value="${attr(v??0)}"></td>`;}
  function editDate(k,v){return `<td><input class="cell-input" data-edit="${attr(k)}" type="date" value="${attr(v||"")}"></td>`;}

  async function createFromForm(e,table){
    e.preventDefault(); const form=e.currentTarget, fd=new FormData(form),body={};
    for(const [k,v] of fd) body[k]=v;
    for(const k of ["budget","actual","paid","needed","bought","unit_cost","total"]) if(k in body)body[k]=Number(body[k])||0;
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

  async function delegatedClick(e){
    const b=e.target.closest("[data-action]"); if(!b)return;
    if(b.dataset.action==="edit-guest"){const g=(state.guests||[]).find(x=>x.id===b.dataset.id);if(g)openGuest(g);return;}
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
    const s=state.settings||{},t=s.ticket||{},b=s.bank||{},c=s.ceremony||{},f=s.celebration||{};
    $("ticketEnabled").checked=t.enabled!==false; $("ticketPriceInput").value=t.price??0; $("ticketTextInput").value=t.text||"";
    $("bankHolderInput").value=b.holder||""; $("bankAliasInput").value=b.alias||""; $("bankCbuInput").value=b.cbu||""; $("bankMpInput").value=b.mp_url||"";
    $("ceremonyTimeInput").value=c.time||""; $("ceremonyPlaceInput").value=c.place||""; $("ceremonyAddressInput").value=c.address||""; $("ceremonyLatInput").value=c.lat??""; $("ceremonyLngInput").value=c.lng??"";
    $("celebrationTimeInput").value=f.time||""; $("celebrationPlaceInput").value=f.place||""; $("celebrationAddressInput").value=f.address||""; $("celebrationLatInput").value=f.lat??""; $("celebrationLngInput").value=f.lng??"";
    $("deadlineInput").value=s.rsvp_deadline_display||""; $("fallbackWaInput").value=s.fallback_whatsapp||"";
  }

  async function saveSettings(){
    const old=state.settings||{};
    const settings={...old,
      rsvp_deadline_display:$("deadlineInput").value.trim(),fallback_whatsapp:$("fallbackWaInput").value.replace(/\D/g,""),
      ticket:{...(old.ticket||{}),enabled:$("ticketEnabled").checked,price:Number($("ticketPriceInput").value)||0,currency:"ARS",text:$("ticketTextInput").value.trim()},
      bank:{holder:$("bankHolderInput").value.trim(),alias:$("bankAliasInput").value.trim(),cbu:$("bankCbuInput").value.replace(/\s/g,""),mp_url:$("bankMpInput").value.trim()},
      ceremony:{...(old.ceremony||{}),time:$("ceremonyTimeInput").value.trim(),place:$("ceremonyPlaceInput").value.trim(),address:$("ceremonyAddressInput").value.trim(),lat:Number($("ceremonyLatInput").value),lng:Number($("ceremonyLngInput").value)},
      celebration:{...(old.celebration||{}),time:$("celebrationTimeInput").value.trim(),place:$("celebrationPlaceInput").value.trim(),address:$("celebrationAddressInput").value.trim(),lat:Number($("celebrationLatInput").value),lng:Number($("celebrationLngInput").value)}
    };
    try{await api("/api/admin/settings",{method:"PUT",body:settings});await loadState();status("Sitio y tarjeta actualizados.");}
    catch(err){status(err.message,"err",5000);}
  }

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
        name:g.name||"Invitado",phone:g.phone||"",email:g.email||"",
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
    const head=["Nombre","Estado","Asistencia","Lugares","Telefono","Email","TarjetaUnit","TarjetaPagada","Regalo","Mesa","Menu","Cancion","Notas"];
    const rows=(state.guests||[]).map(g=>[g.name,statusLabel(g.status),g.attendance,g.seats,g.phone,g.email,guestUnit(g),g.ticket_paid,g.gift_amount,g.table_no,g.diet,g.song,g.notes].map(csvCell).join(","));
    download("invitados-boda.csv","\ufeff"+[head.map(csvCell).join(","),...rows].join("\r\n"),"text/csv;charset=utf-8");
  }
})();
