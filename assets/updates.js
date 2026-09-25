(() => {
  "use strict";
  const release = document.querySelector('meta[name="wedding-release"]')?.content;
  const draftKey = "wedding_update_draft";
  let checking = false;
  let navigating = false;

  function restoreDraft(){
    try{
      const draft = JSON.parse(sessionStorage.getItem(draftKey) || "null");
      sessionStorage.removeItem(draftKey);
      if(!draft || Date.now()-draft.savedAt > 30*60*1000) return;
      const fields = document.querySelectorAll('#rsvpForm input, #rsvpForm select, #rsvpForm textarea');
      for(const saved of draft.fields){
        const field = Array.from(fields).find(el=>el.id===saved.id && el.name===saved.name && (el.type!=="radio" || el.value===saved.value));
        if(!field) continue;
        if(field.type==="radio" || field.type==="checkbox") field.checked=saved.checked;
        else {
          // The initial HTML only contains one seat; restore the chosen value
          // before syncSeatLimit revalidates it against the server's allowance.
          if(field.id==="seats" && /^[1-9]$|^1[0-2]$/.test(saved.value) &&
             !Array.from(field.options).some(option=>option.value===saved.value)){
            const option=document.createElement("option");
            option.value=saved.value;
            option.textContent=`${saved.value} personas`;
            field.appendChild(option);
          }
          field.value=saved.value;
        }
      }
      document.querySelector('#rsvpForm input[name="attendance"]:checked')?.dispatchEvent(new Event("change",{bubbles:true}));
    }catch(_){}
  }

  async function checkRelease(){
    if(checking || navigating || document.hidden || !navigator.onLine) return;
    checking = true;
    const ctrl = new AbortController();
    const timer = setTimeout(()=>ctrl.abort(),10000);
    try{
      const url = new URL(window.location.href);
      url.hash="";
      url.searchParams.set("_release_check",String(Date.now()));
      const response = await fetch(url,{cache:"no-store",signal:ctrl.signal});
      if(!response.ok) return;
      const page = new DOMParser().parseFromString(await response.text(),"text/html");
      const next = page.querySelector('meta[name="wedding-release"]')?.content;
      if(!next || next===release) return;
      // Do not interrupt an RSVP submission already in flight.
      if(document.querySelector('#rsvpForm button[type="submit"]')?.disabled) return;
      const fields = Array.from(document.querySelectorAll('#rsvpForm input, #rsvpForm select, #rsvpForm textarea'))
        .map(el=>({id:el.id,name:el.name,value:el.value,checked:el.checked}));
      // If storage is unavailable, leave an unfinished form intact.
      sessionStorage.setItem(draftKey,JSON.stringify({savedAt:Date.now(),fields}));
      const target = new URL(window.location.href);
      target.searchParams.set("_v",next);
      target.searchParams.delete("_release_check");
      navigating = true;
      window.location.replace(target.href);
    }catch(_){}finally{ clearTimeout(timer); checking=false; }
  }

  window.addEventListener("pageshow",()=>{restoreDraft();checkRelease();});
  window.addEventListener("online",checkRelease);
  document.addEventListener("visibilitychange",checkRelease);
  setInterval(checkRelease,60000);
})();
