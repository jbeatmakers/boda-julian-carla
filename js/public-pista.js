/* Pista pública anónima + YouTube (sin Premium). */
(function () {
    const PISTA_KEY = "boda_julian_carla_pista";
    const CONFIG_KEY = "boda_julian_carla_config";
    const GUESTS_KEY = "boda_julian_carla_guests";

    function uniqueSongs(lists) {
        const seen = new Set();
        const out = [];
        lists.flat().forEach(function (item) {
            const title = (item && (item.title || item.song) || "").trim();
            if (!title) return;
            const k = title.toLowerCase();
            if (seen.has(k)) return;
            seen.add(k);
            out.push({ title: title });
        });
        return out;
    }

    function saveLocal(title) {
        const list = JSON.parse(localStorage.getItem(PISTA_KEY) || "[]");
        if (!list.some(function (s) { return (s.title || "").toLowerCase() === title.toLowerCase(); })) {
            list.push({ title: title, at: new Date().toISOString() });
            localStorage.setItem(PISTA_KEY, JSON.stringify(list));
        }
    }

    function render(songs, playlistId) {
        const mount = document.getElementById("pistaPublica");
        if (!mount) return;
        const listEl = document.getElementById("pistaSongList");
        const frame = document.getElementById("pistaPlayer");
        const empty = document.getElementById("pistaEmpty");
        if (listEl) {
            listEl.innerHTML = songs.map(function (s) {
                return '<li class="py-1 border-b border-hairline/80">' + s.title.replace(/[<>]/g, "") + "</li>";
            }).join("");
        }
        if (empty) empty.classList.toggle("hidden", songs.length > 0);
        if (frame) {
            if (playlistId) {
                frame.classList.remove("hidden");
                frame.src = "https://www.youtube-nocookie.com/embed/videoseries?list=" + encodeURIComponent(playlistId);
            } else {
                frame.classList.add("hidden");
                frame.removeAttribute("src");
            }
        }
    }

    async function boot() {
        let fileSongs = [];
        let playlistId = "";
        try {
            const res = await fetch("pista.json", { cache: "no-store" });
            if (res.ok) {
                const data = await res.json();
                fileSongs = data.songs || [];
                playlistId = data.youtubePlaylistId || "";
            }
        } catch (e) {}
        try {
            const cfg = JSON.parse(localStorage.getItem(CONFIG_KEY) || "{}");
            if (cfg.youtubePlaylistId) playlistId = cfg.youtubePlaylistId;
        } catch (e) {}
        let local = [];
        let fromGuests = [];
        try { local = JSON.parse(localStorage.getItem(PISTA_KEY) || "[]"); } catch (e) {}
        try {
            const guests = JSON.parse(localStorage.getItem(GUESTS_KEY) || "[]");
            fromGuests = guests.map(function (g) { return { title: g.song }; });
        } catch (e) {}
        render(uniqueSongs([fileSongs, local, fromGuests]), playlistId);
    }

    document.addEventListener("DOMContentLoaded", function () {
        boot();
        const form = document.getElementById("rsvpForm");
        if (form) {
            form.addEventListener("submit", function () {
                const song = (document.getElementById("songRequest") || {}).value;
                if (song && song.trim()) {
                    saveLocal(song.trim());
                    boot();
                }
            });
        }
    });
})();
