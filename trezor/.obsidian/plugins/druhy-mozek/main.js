/* Druhý mozek – rozšíření trezoru (KISK FF MU).
 * Doplňuje plugin Neuro Roadmap (plánování) o: zpracování materiálů AI, frontu bez AI,
 * nové úkoly a převod prací do šablony KISK ve Wordu, týdenní přehled, přípravu na zkoušku,
 * kontrolu a hlídání kódu, automatickou zálohu a rozhraní ve 4 jazycích (cs, sk, en, uk).
 * Logika běží ve skriptech v _Systém/ (priprav.py, novy_ukol.py) a v AI (.claude/commands).
 * Texty: čeština je přímo v kódu, ostatní jazyky v preklady.json (klíč = český text).
 */
const { Plugin, PluginSettingTab, Modal, Setting, Notice, FuzzySuggestModal, Menu, TFile, requestUrl } = require("obsidian");
const { execFile } = require("child_process");
const fs = require("fs");
const crypto = require("crypto");
const path = require("path");
const os = require("os");

// Python a Claude Code hledáme na obvyklých místech (Homebrew na Apple Silicon / Intel, systém, instalátor Claude)
const najdi = (kandidati) => kandidati.find((p) => fs.existsSync(p)) || kandidati[0];
const PYTHON = najdi(["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]);
const CLAUDE = najdi(["/opt/homebrew/bin/claude", "/usr/local/bin/claude",
  path.join(os.homedir(), ".local/bin/claude"), path.join(os.homedir(), ".claude/local/claude")]);
const DOMOV = "00 Domov.md";
const FRONTA = "_Systém/Fronta.md";
const ZPRAVA = "_Systém/Kontrola druhého mozku.md";
const ROADMAP_ID = "neuro-roadmap";
const ROADMAP_PRIKAZ = "neuro-roadmap:open-neuro-adaptive-roadmap";
const IGNOROVAT = ["md", "base", "canvas", "json"];
const KONTROLA_KAZDYCH_MS = 6 * 60 * 60 * 1000;

// Aktualizace: jednou denně se zeptá GitHubu na číslo poslední verze (nic se neodesílá, nic se samo neinstaluje)
const REPOZITAR = "shadowsh1t/second-brain-kisk";
// Odkud je rozšíření: "github" = instalátor z GitHubu (aktualizace jedním klikem), "obsidian" = adresář rozšíření Obsidianu
// (aktualizuje Obsidian; systém pro trezor je přibalený v BALIK). Obojí doplňuje nastroje/sestav_rozsireni.py.
const DISTRIBUCE = "github";
const BALIK = null;
// stejné jako VZDY_NAHRADIT v nastroje/aktualizace.py (Obsidian tabulky sám přeformátuje, takže by vypadaly jako upravené)
const VZDY_NAHRADIT = ["_Systém/Studium.base"];
const JEN_VYTVORIT = ["_Inbox/Inbox.md", "_Pojmy/Pojmy.md", "_Přehledy/Přehledy.md"];  // rozcestníky patří uživateli
const PRIPONA_NOVA_VERZE = { cs: " (nová verze)", sk: " (nová verzia)", en: " (new version)", uk: " (нова версія)" };
const AKTUALIZACE_KAZDYCH_MS = 24 * 60 * 60 * 1000;
const VERZE = /^v?(\d+)\.(\d+)\.(\d+)$/;
const novejsiVerze = (a, b) => {
  const x = VERZE.exec(String(a)), y = VERZE.exec(String(b));
  if (!x || !y) return false;
  for (let i = 1; i <= 3; i++) if (Number(x[i]) !== Number(y[i])) return Number(x[i]) > Number(y[i]);
  return false;
};
const MAX_BALIK = 50 * 1024 * 1024;
// Hlášení chyb: nic se neodesílá samo – uživatel vše vidí, může upravit a odešle sám (e-mailem nebo na GitHubu)
const HLASENI_EMAIL = "catty.skipping888@passinbox.com";
const MAX_ZAZNAMU_CHYB = 15;
const KARTICKY_INTERVALY = [1, 2, 4, 8, 16, 32];  // dny mezi opakováními podle „krabičky“ (Leitner)
const KARTICKY_ZA_SEZENI = 30;
const dv = (n) => String(n).padStart(2, "0");
const dnesniDatum = (posun = 0) => { const d = new Date(Date.now() + posun * 86400000); return `${d.getFullYear()}-${dv(d.getMonth() + 1)}-${dv(d.getDate())}`; };
const dnyDo = (iso) => Math.round((Date.parse(String(iso).slice(0, 10) + "T00:00:00") - Date.parse(dnesniDatum() + "T00:00:00")) / 86400000);
const MANIFEST_ROZSIRENI = ".obsidian/plugins/druhy-mozek/manifest.json";
const ZALOHA_AKTUALIZACE_DNI = 7;  // dočasná záloha z aktualizace zůstává týden – kvůli ↩️ Vrátit poslední aktualizaci
const spust = (prikaz, argumenty, moznosti = {}) => new Promise((ok, chyba) =>
  execFile(prikaz, argumenty, { timeout: 300000, ...moznosti },
    (err, stdout, stderr) => (err ? chyba(new Error(String(stderr || err.message).trim())) : ok(String(stdout)))));
const souboryVeSlozce = (koren, rel = "") => fs.readdirSync(path.join(koren, rel), { withFileTypes: true }).flatMap((e) => {
  const r = rel ? `${rel}/${e.name}` : e.name;
  return e.isDirectory() ? souboryVeSlozce(koren, r) : e.isFile() ? [r] : [];
});
const otiskSouboru = (cesta) => crypto.createHash("sha256").update(fs.readFileSync(cesta)).digest("hex");
const bezpecnaCesta = (rel) => typeof rel === "string" && rel && !path.isAbsolute(rel) && !rel.split("/").includes("..");
// otevírat jen stránky tohoto repozitáře na GitHubu
const odkazRepozitare = (url, cesta = "") => {
  try {
    const u = new URL(String(url));
    return u.origin === "https://github.com" && u.pathname.startsWith(`/${REPOZITAR}/${cesta}`) && !String(url).includes("..")
      ? u.href : null;
  } catch (e) {
    return null;
  }
};

// Jazyky rozhraní (a dokumentů ve Wordu)
const JAZYKY = { cs: "Čeština", sk: "Slovenčina", en: "English", uk: "Українська" };
const LOKALE = { cs: "cs-CZ", sk: "sk-SK", en: "en-GB", uk: "uk-UA" };
// Poslední krok úkolu („Odevzdat…“) ve všech jazycích – pro označení jako odevzdaný
const KROK_ODEVZDAT = /^- \[ \] ((?:Odevzdat|Odovzdať|Submit|Здати).*)$/m;

// Automatická záloha: po změnách (s odstupem), po potvrzení kódu/nastavení a aspoň jednou denně
const ZALOHA_PO_ZMENE_MS = 10 * 60 * 1000;
const ZALOHA_DENNE_MS = 24 * 60 * 60 * 1000;
const ZALOHA_VERZE = /^\d{4}-\d{2}-\d{2} \d{2}\.\d{2}(\.\d{2})?$/;
const ZALOHA_VYNECHAT = ["_Systém/cache", "_Systém/Inspirace", ".druhy-mozek-zaloha", ".obsidian/plugins/copilot", ".obsidian/plugins/neuro-roadmap", ".trash", ".git"];
const ZALOHA_BEZ_ZMENY = ["_Systém/Fronta.md", "_Systém/fronta.json", "_Systém/registr.json", "_Systém/Kontrola druhého mozku.md"];
const ZALOHA_VZDY = ["_Systém/Word/logo-muni-arts.png"];
const MATERIAL = /\.(pdf|pptx?|docx?|rtf|webloc|png|jpe?g|heic|webp|gif|zip|mp4|mov|mp3|m4a)$/i;

// Co musí Neuro Roadmap umět přečíst z našich poznámek (doplňujeme do jeho nastavení)
const MAPOVANI_VLASTNOSTI = { subject: "kod", semester: "semestr", dueDate: "termin", status: "stav", type: "typ", priority: "priorita" };
const MAPOVANI_HODNOT = {
  statusTodo: "otevreno, otevřeno", statusInProgress: "rozpracovano, rozpracováno", statusDone: "hotovo, odevzdano, odevzdáno",
  typeTask: "ukol, úkol", calendarAssignmentDeadline: "ukol, úkol", calendarExam: "zkouska, zkouška, test",
  priorityHigh: "vysoka, vysoká", priorityLow: "nizka, nízká",
};
const VYLOUCENE_SLOZKY = ["_Systém/", ".claude/", "_Archiv/"];
const SOUBORY_SYSTEMU = ["_Systém/priprav.py", "_Systém/novy_ukol.py", "_Systém/predmety.py", "_Systém/prehledy.py", "_Systém/nastaveni.json", "_Systém/texty.json",
  "_Systém/Word/Šablona KISK.dotx", "_Systém/Studium.base", ".claude/CLAUDE.md"];

// Soubory, které spouští kód, řídí AI nebo tvoří obsah systému – jejich změnu musí uživatel potvrdit
const CHRANENE = [
  "_Systém/priprav.py", "_Systém/novy_ukol.py", "_Systém/predmety.py", "_Systém/prehledy.py", "_Systém/Word/vytvor_sablonu.py",
  "_Systém/nastaveni.json",
  "_Systém/texty.json",
  "_Systém/jazyky/cs.json", "_Systém/jazyky/sk.json", "_Systém/jazyky/en.json", "_Systém/jazyky/uk.json",
  ".obsidian/plugins/druhy-mozek/main.js", ".obsidian/plugins/druhy-mozek/manifest.json", ".obsidian/plugins/druhy-mozek/preklady.json",
  ".claude/settings.json", ".claude/CLAUDE.md",
  ".claude/commands/zpracuj.md", ".claude/commands/tyden.md", ".claude/commands/zkouska.md", ".claude/commands/oprav-roadmap.md",
];

// Příkaz jiné AI: jen bezpečné znaky + značka {prompt} (žádné ; | & $ ` uvozovky apod.)
const BEZPECNY_AI_PRIKAZ = /^[A-Za-z0-9 _./=:-]*\{prompt\}[A-Za-z0-9 _./=:-]*$/;

// ---------- Překlady ----------
let JAZYK = "cs";
let SLOVNIK = {};
const T = (cesky, ...argy) => String(SLOVNIK[cesky] ?? cesky).replace(/\{(\d)\}/g, (_, i) => (argy[i] ?? ""));
const kdy = (iso, kratce) => new Date(iso).toLocaleString(LOKALE[JAZYK] || "cs-CZ",
  kratce ? { day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" } : undefined);

const doplnSeznam = (puvodni, pridat) => {
  const cast = String(puvodni || "").split(",").map((x) => x.trim()).filter(Boolean);
  const chybi = pridat.split(",").map((x) => x.trim()).filter((x) => x && !cast.includes(x));
  return { hodnota: [...cast, ...chybi].join(", "), chybi };
};

const shellUvozovky = (s) => "'" + String(s).replace(/'/g, "'\\''") + "'";
const asUvozovky = (s) => '"' + String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';

module.exports = class DruhyMozek extends Plugin {
  async onload() {
    this.zaklad = this.app.vault.adapter.basePath;
    this.nactiJazyk();
    this.data = Object.assign({ roadmapPrikaz: ROADMAP_PRIKAZ, posledniVerze: null, kontrola: null }, await this.loadData());
    this.data.zaloha = Object.assign({ zapnuto: true, slozka: this.vychoziSlozkaZalohy(), pocet: 10, materialy: false,
      posledni: null, chyba: null }, this.data.zaloha || {});
    this.data.aktualizace = Object.assign({ kontrolovat: true, posledni: null, nejnovejsi: null, chyba: null }, this.data.aktualizace || {});
    this.data.pripominky = Object.assign({ zapnuto: true, den: null }, this.data.pripominky || {});
    this.data.karticky = this.data.karticky || {};
    this.data.chyby = Array.isArray(this.data.chyby) ? this.data.chyby.slice(-MAX_ZAZNAMU_CHYB) : [];

    this.addRibbonIcon("brain", this.manifest.name, (evt) => this.ukazMenu(evt));
    this.addSettingTab(new NastaveniTab(this.app, this));
    this.registrujPrikazy();

    // ```druhy-mozek``` v poznámce vykreslí tlačítka akcí, ```druhy-mozek-stav``` stav kontroly (obojí na Domově)
    this.registerMarkdownCodeBlockProcessor("druhy-mozek", (zdroj, el) => this.vykresliTlacitka(zdroj, el));
    this.bannery = new Set();
    this.registerMarkdownCodeBlockProcessor("druhy-mozek-stav", (zdroj, el) => { this.bannery.add(el); this.vykresliStav(el); });

    this.stavovyRadek = this.addStatusBarItem();
    this.stavovyRadek.addClass("mod-clickable", "druhy-mozek-stav-radek");
    this.stavovyRadek.addEventListener("click", () => this.app.workspace.openLinkText(ZPRAVA, "", true));
    this.aktualizujStavovyRadek();

    // kontrola: po startu, pak každých 6 hodin (zachytí i aktualizaci Neuro Roadmap)
    this.app.workspace.onLayoutReady(() => setTimeout(() => this.kontrola({ automaticky: true }), 8000));
    // verze z adresáře Obsidianu: první spuštění → průvodce; po aktualizaci rozšíření → nabídnout obnovu souborů v trezoru
    this.app.workspace.onLayoutReady(() => setTimeout(() => this.zkontrolujPribalenySystem(), 2500));
    this.registerInterval(window.setInterval(() => this.kontrola({ automaticky: true }), KONTROLA_KAZDYCH_MS));

    // nová verze: po startu a pak jednou denně („Teď ne“ = zeptá se znovu po dalším spuštění Obsidianu)
    this.app.workspace.onLayoutReady(() => setTimeout(() => this.zkontrolujAktualizace({ automaticky: true }), 15000));
    // připomínky termínů: po startu a pak každou hodinu (ukážou se jednou za den)
    this.app.workspace.onLayoutReady(() => setTimeout(() => this.pripomenTerminy({}), 12000));
    this.registerInterval(window.setInterval(() => this.pripomenTerminy({}), 60 * 60 * 1000));
    this.registerInterval(window.setInterval(() => this.zkontrolujAktualizace({ automaticky: true }), AKTUALIZACE_KAZDYCH_MS));

    this.app.workspace.onLayoutReady(() => {
      // vzhled předmětů (druhy-mozek-predmety.css) zapnout jednou – po aktualizaci ze starší verze, kde nebyl
      const css = this.app.customCss;
      if (!this.data.predmetyCss && css?.setCssEnabledStatus &&
          fs.existsSync(path.join(this.zaklad, ".obsidian", "snippets", "druhy-mozek-predmety.css"))) {
        css.setCssEnabledStatus("druhy-mozek-predmety", true);
        this.data.predmetyCss = true;
        this.saveData(this.data);
      }

      // fronta se přepočítá sama, když do trezoru přibude nebo se změní materiál (lokálně, bez AI)
      const hlidej = (f) => {
        if (!(f instanceof TFile) || f.path.startsWith("_Systém/") || IGNOROVAT.includes(f.extension)) return;
        this.naplanujFrontu();
      };
      this.registerEvent(this.app.vault.on("create", hlidej));
      this.registerEvent(this.app.vault.on("rename", hlidej));
      this.registerEvent(this.app.vault.on("modify", hlidej));

      // automatická záloha po změně čehokoli v trezoru (kromě souborů, které se mění samy)
      const zmena = (f) => {
        const cesta = f?.path || "";
        if (ZALOHA_BEZ_ZMENY.includes(cesta) || ZALOHA_VYNECHAT.some((v) => cesta.startsWith(v))) return;
        this.naplanujZalohu();
      };
      for (const udalost of ["create", "modify", "rename", "delete"]) this.registerEvent(this.app.vault.on(udalost, zmena));
      setTimeout(() => {
        const z = this.data.zaloha;
        if (z.zapnuto && (!z.posledni || Date.now() - Date.parse(z.posledni) > ZALOHA_DENNE_MS)) this.zalohuj({ tise: true });
      }, 60000);
      this.registerInterval(window.setInterval(() => {
        const z = this.data.zaloha;
        if (z.zapnuto && Date.now() - Date.parse(z.posledni || 0) > ZALOHA_DENNE_MS) this.zalohuj({ tise: true });
      }, 60 * 60 * 1000));
    });
  }

  onunload() {
    clearTimeout(this.casovacFronty);
    clearTimeout(this.casovacZalohy);
    // po vypnutí/znovunačtení rozšíření by staré upozornění zůstalo viset vedle nového
    this.posledniUpozorneni?.hide();
    this.posledniUpozorneni = null;
  }

  // Verze z manifest.json na disku – this.manifest si Obsidian pamatuje z prvního načtení,
  // takže po aktualizaci bez restartu by ukazoval starou verzi
  verze() {
    try {
      const v = JSON.parse(fs.readFileSync(path.join(this.zaklad, this.manifest.dir, "manifest.json"), "utf8")).version;
      if (VERZE.test(String(v))) return String(v);
    } catch (e) { /* záloha níže */ }
    return this.manifest.version;
  }

  // ---------- Jazyk ----------

  nactiJazyk() {
    this.nastavJazykRozhrani(this.nastaveni().jazyk);
  }

  nastavJazykRozhrani(jazyk) {
    JAZYK = JAZYKY[jazyk] ? jazyk : "cs";
    SLOVNIK = {};
    if (JAZYK === "cs") return;
    try {
      SLOVNIK = JSON.parse(fs.readFileSync(path.join(this.zaklad, this.manifest.dir, "preklady.json"), "utf8"))[JAZYK] || {};
    } catch (e) {
      SLOVNIK = BALIK?.preklady?.[JAZYK] || {};
    }
  }

  // Přepíše systémové poznámky (Domov, Návod, šablony, rozcestníky, tabulky) jazykovým balíčkem; tvoje poznámky nemění
  async aplikujJazykovyBalicek(jazyk) {
    const balicek = JSON.parse(fs.readFileSync(path.join(this.zaklad, "_Systém", "jazyky", `${jazyk}.json`), "utf8"));
    let zapsano = 0;
    for (const [rel, obsah] of Object.entries(balicek.soubory || {})) {
      if (path.isAbsolute(rel) || rel.split("/").includes("..")) continue;
      if (rel.startsWith("Příklad předmětu/") && !(await this.app.vault.adapter.exists(rel))) continue;
      const slozka = path.posix.dirname(rel);
      if (slozka !== "." && !(await this.app.vault.adapter.exists(slozka))) await this.app.vault.adapter.mkdir(slozka);
      await this.app.vault.adapter.write(rel, obsah);
      zapsano++;
    }
    return zapsano;
  }

  // Příkazy v paletě; po změně jazyka se přejmenují na místě – rozšíření se samo nevypíná ani nezapíná (pravidla adresáře)
  registrujPrikazy() {
    if (typeof this.removeCommand === "function") for (const id of this.prikazy || []) this.removeCommand(id);
    this.prikazy = [];
    for (const a of this.akce()) {
      this.addCommand({ id: a.id, name: a.nazev, callback: a.spust });
      this.prikazy.push(a.id);
    }
  }

  // ---------- Akce ----------

  jeNastaveno() {
    return fs.existsSync(path.join(this.zaklad, "_Systém", "nastaveni.json"));
  }

  akce() {
    if (BALIK && !this.jeNastaveno()) {
      return [{ id: "nastavit", ikona: "brain", nazev: T("🧠 Nastavit druhý mozek v tomto trezoru"), spust: () => new PruvodceModal(this).open() }];
    }
    const bezAI = this.rezimAI() === "zadna";
    return this.vsechnyAkce().filter((a) => !(bezAI && a.ai) && !(a.jenGithub && DISTRIBUCE !== "github"));
  }

  vsechnyAkce() {
    const bezAI = this.rezimAI() === "zadna";
    return [
      { id: "zpracuj", ai: true, ikona: "inbox", nazev: T("📥 Zpracovat nové materiály (AI)"), spust: () => this.claude("/zpracuj") },
      { id: "fronta", ikona: "search", nazev: T("🔎 Co čeká na zpracování (bez AI)"), spust: () => this.ukazFrontu() },
      { id: "poznamka", ikona: "file-pen", nazev: T("📝 Nová poznámka k materiálu"),
        spust: () => new MaterialVyber(this, (m) => this.novaPoznamka(m), T("Ke kterému materiálu chceš psát poznámku?")).open() },
      { id: "rucne-hotovo", jenRucne: true, ikona: "check", nazev: T("✔️ Označit materiál jako zpracovaný (ručně)"), spust: () => new MaterialVyber(this).open() },
      { id: "novy-ukol", ikona: "file-plus", nazev: T("📝 Nový úkol ve Wordu (šablona KISK)"), spust: () => new UkolModal(this).open() },
      { id: "prevod", ikona: "file-input", nazev: T("📄 Převést hotovou práci do šablony KISK"), spust: () => new DocxVyber(this).open() },
      { id: "hotovo", ikona: "check-circle", nazev: T("✅ Označit úkol jako odevzdaný"), spust: () => this.oznacHotovo() },
      { id: "roadmap", ikona: "gantt-chart", nazev: T("🧭 Plán úkolů (Neuro Roadmap)"), spust: () => this.otevriRoadmap() },
      { id: "tyden", ikona: "calendar-days", nazev: bezAI ? T("🗓 Týdenní přehled") : T("🗓 Týdenní přehled (AI)"),
        spust: () => (bezAI ? this.vygeneruj(["--tyden"]) : this.claude("/tyden")) },
      { id: "zkouska", ikona: "graduation-cap", nazev: bezAI ? T("🎓 Příprava na zkoušku") : T("🎓 Příprava na zkoušku (AI)"),
        spust: () => new PredmetVyber(this, (p) => (bezAI ? this.vygeneruj(["--zkouska", p.nazev]) : this.claude("/zkouska " + p.nazev))).open() },
      { id: "karticky", ikona: "layers", nazev: T("🃏 Opakovat kartičky"), spust: () => new KartickyModal(this).open() },
      { id: "kalendar", ikona: "calendar-plus", nazev: T("📅 Termíny do kalendáře"), spust: () => this.doKalendare() },
      { id: "citace", ikona: "quote", nazev: T("📚 Citace zdroje (ČSN ISO 690)"), spust: () => new CitaceModal(this).open() },
      { id: "pripominky", ikona: "alarm-clock", nazev: T("⏰ Blížící se termíny"), spust: () => this.pripomenTerminy({ vzdy: true }) },
      { id: "predmet", ikona: "book-plus", nazev: T("📚 Přidat předmět"), spust: () => new PredmetNovyModal(this).open() },
      { id: "hlaseni", ikona: "bug", nazev: T("🐞 Nahlásit chybu nebo nápad"), spust: () => new HlaseniModal(this).open() },
      { id: "zalohovat", ikona: "hard-drive-upload", nazev: T("💾 Zálohovat teď"), spust: () => this.zalohuj({ tise: false }) },
      { id: "aktualizace", jenGithub: true, ikona: "refresh-cw", nazev: T("🔄 Zkontrolovat novou verzi"), spust: () => this.zkontrolujAktualizace({ automaticky: false }) },
      { id: "nastaveni", ikona: "settings", nazev: T("⚙️ Nastavení (AI, záloha, jazyky, jméno)"), spust: () => this.otevriNastaveni() },
      { id: "domov", ikona: "home", nazev: T("🏠 Otevřít Domov"), spust: () => this.app.workspace.openLinkText(DOMOV, "", false) },
      { id: "kontrola", ikona: "stethoscope", nazev: T("🩺 Zkontrolovat propojení"), spust: () => this.kontrola({ automaticky: false }) },
      { id: "potvrdit-kod", ikona: "shield-check", nazev: T("🛡 Potvrdit změny kódu (byly moje)"), spust: () => this.potvrdIntegritu() },
      { id: "oprava-ai", ai: true, ikona: "wrench", nazev: T("🔧 Nechat AI opravit propojení s Neuro Roadmap"), spust: () => this.claude("/oprav-roadmap") },
    ];
  }

  // ---------- Předměty ----------

  async pridejPredmet(kod, nazev) {
    const vystup = await this.spustPython("predmety.py", ["--pridat", `${kod} ${nazev}`.trim()]);
    new Notice(vystup || T("📚 Předmět přidán."), 8000);
  }

  // Odebrání = přesun celé složky předmětu do koše v macOS (dá se vrátit), jen po potvrzení
  async odeberPredmet(nazev) {
    const slozka = this.app.vault.getAbstractFileByPath(nazev);
    if (!slozka || nazev.includes("/") || nazev.startsWith("_") || nazev.startsWith(".")) {
      new Notice(T("Předmět {0} nebyl nalezen.", nazev));
      return;
    }
    await this.app.vault.trash(slozka, true);
    try { await this.spustPython("predmety.py", ["--css"]); } catch (e) { /* vzhled se opraví při dalším přidání */ }
    new Notice(T("🗑 Předmět {0} je v koši – vrátit ho můžeš z koše ve Finderu.", nazev), 10000);
  }

  // ---------- Verze z adresáře Obsidianu: přibalený systém pro trezor ----------

  // Soubory systému pro daný jazyk: kód + systémové poznámky z jazykového balíčku (+ ukázkový předmět)
  balikProJazyk(jazyk) {
    const j = JAZYKY[jazyk] ? jazyk : "cs";
    const soubory = { ...BALIK.soubory };
    const balicek = JSON.parse(BALIK.soubory[`_Systém/jazyky/${j}.json`].text).soubory;
    for (const [rel, text] of Object.entries(balicek)) {
      soubory[rel] = { druh: rel.startsWith("Příklad předmětu/") ? "ukazka" : VZDY_NAHRADIT.includes(rel) ? "kod" : JEN_VYTVORIT.includes(rel) ? "uzivatelske" : "upravitelne", text };
    }
    return soubory;
  }

  async pythonFunguje() {
    try { return /Python 3/.test(await spust(PYTHON, ["--version"], { timeout: 15000 })); } catch (e) { return false; }
  }

  async zkontrolujPribalenySystem() {
    if (!BALIK) return;
    if (!this.jeNastaveno()) { new PruvodceModal(this).open(); return; }
    let ev = {};
    try { ev = JSON.parse(fs.readFileSync(path.join(this.zaklad, "_Systém", "instalace.json"), "utf8")); } catch (e) { /* starší instalace */ }
    if (novejsiVerze(BALIK.verze, ev.verze || "0.0.0")) new ObnovaSouboruModal(this, ev.verze || "?").open();
  }

  zapisEvidenci(soubory) {
    const otiskTextu = (t) => crypto.createHash("sha256").update(t, "utf8").digest("hex");
    const evidence = {};
    for (const [rel, f] of Object.entries(soubory)) {
      const cil = path.join(this.zaklad, rel);
      try { if (f.druh !== "ukazka" && fs.readFileSync(cil, "utf8") === f.text) evidence[rel] = otiskTextu(f.text); } catch (e) { /* soubor chybí */ }
    }
    fs.writeFileSync(path.join(this.zaklad, "_Systém", "instalace.json"),
      JSON.stringify({ verze: BALIK.verze, jazyk: JAZYK, soubory: evidence }, null, 1) + "\n");
  }

  // 🧠 První nastavení trezoru (to, co jinak dělá Instalovat.command) – nic existujícího se nepřepíše
  async nastavTrezor(v) {
    const soubory = this.balikProJazyk(v.jazyk);
    const predmety = (v.predmety || []).map((x) => x.trim()).filter(Boolean);
    for (const [rel, f] of Object.entries(soubory)) {
      if (!bezpecnaCesta(rel) || (f.druh === "ukazka" && predmety.length)) continue;
      const cil = path.join(this.zaklad, rel);
      if (fs.existsSync(cil)) continue;
      fs.mkdirSync(path.dirname(cil), { recursive: true });
      fs.writeFileSync(cil, f.text);
    }
    if (!predmety.length) for (const d of ["Příklad předmětu/Poznámky", "Příklad předmětu/Úkoly"]) fs.mkdirSync(path.join(this.zaklad, d), { recursive: true });
    const nastaveni = { jmeno: v.jmeno, jmeno_soubor: v.jmenoSoubor, uco: v.uco, ai: v.ai, ai_prikaz: v.ai === "jina" ? v.aiPrikaz : "",
      jazyk: v.jazyk, jazyk_word: v.jazykWord || v.jazyk };
    fs.writeFileSync(path.join(this.zaklad, "_Systém", "nastaveni.json"), JSON.stringify(nastaveni, null, 2) + "\n");
    this.nactiJazyk();
    const sablony = path.join(this.zaklad, this.app.vault.configDir || ".obsidian", "templates.json");
    if (!fs.existsSync(sablony)) fs.writeFileSync(sablony, JSON.stringify({ folder: "_Systém/Šablony", dateFormat: "YYYY-MM-DD" }, null, 2));
    try {  // vestavěné funkce Obsidianu, které systém používá (tabulky Bases, šablony, vlastnosti, plátno)
      for (const id of ["bases", "templates", "properties", "canvas"]) await this.app.internalPlugins?.getPluginById?.(id)?.enable?.(true);
    } catch (e) { /* zapnout jdou i ručně v Nastavení → Základní pluginy */ }
    try {
      for (const css of ["druhy-mozek", "druhy-mozek-predmety"]) this.app.customCss?.setCssEnabledStatus?.(css, true);
      this.data.predmetyCss = true;
    } catch (e) { /* vzhled jde zapnout v Nastavení → Vzhled */ }
    const chyby = [];
    const krok = async (skript, argumenty) => { try { await spust(PYTHON, [path.join("_Systém", skript), ...argumenty], { cwd: this.zaklad }); } catch (e) { chyby.push(e.message); } };
    await krok("Word/vytvor_sablonu.py", []);
    await krok("predmety.py", predmety.length ? ["--pridat", ...predmety] : ["--css"]);
    await krok("priprav.py", []);
    this.zapisEvidenci(soubory);
    delete this.data.otisky;
    this.zmeneneSoubory();  // výchozí otisky = právě nainstalované soubory (žádné 🛡 hned po instalaci)
    await this.saveData(this.data);
    await this.app.workspace.openLinkText(DOMOV, "", false);
    new Notice(T("🎉 Druhý mozek je nastavený. Návod najdeš v poznámce 01 Návod."), 10000);
    if (chyby.length) this.chyba(T("Některé kroky se nepovedly: {0}", chyby.join(" | ")), "nastaveni");
    return chyby;
  }

  // Po aktualizaci rozšíření z Obsidianu: obnova systémových souborů v trezoru (stejná pravidla jako nastroje/aktualizace.py)
  async obnovSoubory() {
    const jazyk = JAZYKY[this.nastaveni().jazyk] ? this.nastaveni().jazyk : "cs";
    const soubory = this.balikProJazyk(jazyk);
    const otiskTextu = (t) => crypto.createHash("sha256").update(t, "utf8").digest("hex");
    let ev = {}, stary = {};
    try { ev = JSON.parse(fs.readFileSync(path.join(this.zaklad, "_Systém", "instalace.json"), "utf8")); } catch (e) { /* starší instalace */ }
    try { stary = JSON.parse(fs.readFileSync(path.join(this.zaklad, "_Systém", "jazyky", `${jazyk}.json`), "utf8")).soubory || {}; } catch (e) { /* bez balíčku */ }
    const evidence = ev.soubory || {};
    const korenZaloh = path.join(this.zaklad, ".druhy-mozek-zaloha");
    if (fs.existsSync(korenZaloh) && fs.lstatSync(korenZaloh).isSymbolicLink()) throw new Error(T("Balík nemá očekávanou podobu."));
    const d = new Date(), nazev = `${d.getFullYear()}-${dv(d.getMonth() + 1)}-${dv(d.getDate())} ${dv(d.getHours())}.${dv(d.getMinutes())}.${dv(d.getSeconds())}`;
    const zaloha = path.join(korenZaloh, nazev);
    const odkaz = (c) => { for (let x = c; x.startsWith(this.zaklad + path.sep); x = path.dirname(x)) { try { if (fs.lstatSync(x).isSymbolicLink()) return true; } catch (e) { /* neexistuje */ } } return false; };
    const v = { nahrazeno: [], nove: [], ponechano: [] };
    try {
      for (const [rel, f] of Object.entries(soubory)) {
        if (f.druh === "ukazka" || !bezpecnaCesta(rel)) continue;
        const cil = path.join(this.zaklad, rel);
        if (odkaz(cil)) continue;
        if (!fs.existsSync(cil)) { fs.mkdirSync(path.dirname(cil), { recursive: true }); fs.writeFileSync(cil, f.text); v.nove.push(rel); continue; }
        if (f.druh === "uzivatelske") continue;
        const soucasny = fs.readFileSync(cil, "utf8");
        if (soucasny === f.text) continue;
        if (f.druh === "kod" || evidence[rel] === otiskTextu(soucasny) || stary[rel] === soucasny) {
          fs.mkdirSync(path.dirname(path.join(zaloha, rel)), { recursive: true });
          fs.copyFileSync(cil, path.join(zaloha, rel));
          fs.writeFileSync(cil, f.text);
          v.nahrazeno.push(rel);
        } else {  // uživatel soubor upravil → nechat, novou verzi uložit vedle
          const vedle = path.join(path.dirname(cil), path.basename(cil, path.extname(cil)) + PRIPONA_NOVA_VERZE[jazyk] + path.extname(cil));
          fs.writeFileSync(vedle, f.text);
          v.ponechano.push(rel);
        }
      }
    } catch (e) {
      for (const rel of v.nahrazeno) fs.copyFileSync(path.join(zaloha, rel), path.join(this.zaklad, rel));
      for (const rel of v.nove) { try { fs.unlinkSync(path.join(this.zaklad, rel)); } catch (x) { /* už není */ } }
      throw e;
    }
    if (v.nahrazeno.length || v.nove.length) {
      this.data.aktualizace.vratit = { slozka: nazev, z: ev.verze || "?", na: BALIK.verze, nove: v.nove,
        nahrazeno: Object.fromEntries(v.nahrazeno.map((rel) => [rel, otiskSouboru(path.join(zaloha, rel))])) };
    }
    this.zapisEvidenci(soubory);
    // obnovu spustil člověk kliknutím → potvrzené jsou jen soubory shodné s balíkem a soubory rozšíření, které dodal Obsidian
    this.data.otisky = this.data.otisky || {};
    for (const [rel, f] of Object.entries(soubory)) { try { if (fs.readFileSync(path.join(this.zaklad, rel), "utf8") === f.text) this.data.otisky[rel] = this.otisk(rel); } catch (e) { /* chybí */ } }
    for (const n of ["main.js", "manifest.json", "styles.css"]) { const rel = `${this.manifest.dir}/${n}`; this.data.otisky[rel] = this.otisk(rel); }
    await this.saveData(this.data);
    try { await this.spustPython("predmety.py", ["--css"]); await this.spustPython("Word/vytvor_sablonu.py", []); } catch (e) { /* zkusí se příště */ }
    new Notice(T("✅ Soubory v trezoru odpovídají verzi {0}.", BALIK.verze) +
      (v.ponechano.length ? " " + T("Upravené soubory zůstaly, nová verze je vedle nich: {0}", v.ponechano.join(", ")) : ""), 12000);
    return v;
  }

  // ---------- Hlášení chyb ----------

  // Odstraní z textu cesty, jméno, UČO a e-maily – do hlášení nesmí nic osobního
  anonymizuj(text) {
    const n = this.nastaveni();
    let t = String(text || "");
    const nahrad = (co, cim) => { if (co && String(co).length > 2) t = t.split(String(co)).join(cim); };
    nahrad(this.zaklad, "<trezor>");
    nahrad(os.homedir(), "~");
    nahrad(n.jmeno, "<jméno>");
    nahrad(n.jmeno_soubor, "<jméno>");
    nahrad(n.uco, "<UČO>");
    for (const cast of String(n.jmeno || "").split(/\s+/)) nahrad(cast.length > 3 ? cast : "", "<jméno>");
    return t.replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, "<e-mail>").replace(/\b\d{6}\b/g, "<číslo>");
  }

  // Zapíše chybu jen lokálně (do dat rozšíření) a ukáže upozornění s tlačítkem 🐞 Nahlásit
  chyba(text, akce = "") {
    if (!Array.isArray(this.data.chyby)) this.data.chyby = [];
    this.data.chyby.push({ cas: new Date().toISOString().slice(0, 16).replace("T", " "), akce, zprava: this.anonymizuj(text).slice(0, 400) });
    this.data.chyby = this.data.chyby.slice(-MAX_ZAZNAMU_CHYB);
    this.saveData(this.data);
    const frag = document.createDocumentFragment();
    frag.createDiv({ text, cls: "druhy-mozek-upozorneni-text" });
    const tl = frag.createEl("button", { text: T("🐞 Nahlásit"), cls: "druhy-mozek-nahlasit" });
    const n = new Notice(frag, 15000);
    tl.addEventListener("click", (e) => { e.stopPropagation(); n.hide(); new HlaseniModal(this, text).open(); });
    return n;
  }

  // Technické údaje bez osobních dat – uživatel je v okně hlášení vidí a může je upravit nebo smazat
  diagnostika() {
    const n = this.nastaveni();
    const k = this.data.kontrola || {};
    let obsidian = "?";
    try { obsidian = require("obsidian").apiVersion || "?"; } catch (e) { /* jen informace */ }
    const radky = [
      `Druhý mozek: ${this.verze()}`, `Obsidian: ${obsidian}`, `macOS: ${os.release()} (${process.arch})`,
      `Jazyk: ${n.jazyk || "cs"} / Word: ${n.jazyk_word || n.jazyk || "cs"}`, `AI: ${this.rezimAI()}`,
      `Předměty: ${this.predmety().length}`, `Neuro Roadmap: ${this.app.plugins?.manifests?.[ROADMAP_ID]?.version || "–"}`,
      `Kontrola: ${k.celkem || "–"}${(k.body || []).filter((b) => b.stav !== "ok").map((b) => ` · ${b.stav}: ${b.nazev}`).join("")}`,
    ];
    if (this.data.chyby?.length) radky.push("", "Poslední chyby:", ...this.data.chyby.slice(-5).map((c) => `- ${c.cas} ${c.akce ? "[" + c.akce + "] " : ""}${c.zprava}`));
    return this.anonymizuj(radky.join("\n"));
  }

  // ---------- Bez AI: poznámky, přehledy, kalendář, připomínky, archiv ----------

  // Spustí prehledy.py; poslední řádek výstupu je cesta k poznámce
  async vygeneruj(argumenty, { otevrit = true } = {}) {
    try {
      const vystup = await this.spustPython("prehledy.py", argumenty);
      const radky = vystup.split("\n").filter(Boolean);
      const rel = radky.pop();
      if (radky.length) new Notice(radky.join("\n"), 8000);
      if (otevrit && rel?.endsWith(".md")) await this.app.workspace.openLinkText(rel, "", true);
      return rel;
    } catch (e) {
      this.chyba(T("Nepodařilo se: {0}", e.message), argumenty[0]);
      return null;
    }
  }

  async novaPoznamka(m) {
    const rel = await this.vygeneruj(["--poznamka", m.soubor]);
    if (!rel) return;
    const material = this.app.vault.getAbstractFileByPath(m.soubor);  // materiál vedle poznámky – čti a piš zároveň
    if (material instanceof TFile) {
      try { await this.app.workspace.getLeaf("split").openFile(material); } catch (e) { /* jen pohodlí */ }
    }
    this.naplanujFrontu();
  }

  async doKalendare() {
    const rel = await this.vygeneruj(["--kalendar"], { otevrit: false });
    if (!rel) return;
    try {
      await require("electron").shell.openPath(path.join(this.zaklad, rel));  // otevře import do Kalendáře
    } catch (e) {
      new Notice(T("Soubor najdeš v {0} – otevři ho dvojklikem a importuj do kalendáře.", rel), 12000);
    }
  }

  ukolySTerminem() {
    return this.app.vault.getMarkdownFiles()
      .filter((f) => !f.path.startsWith("_Systém/") && !f.path.startsWith("_Archiv/"))
      .map((f) => ({ f, fm: this.app.metadataCache.getFileCache(f)?.frontmatter }))
      .filter((x) => ["ukol", "zkouska"].includes(x.fm?.typ) && x.fm.stav !== "hotovo" && /^\d{4}-\d{2}-\d{2}/.test(String(x.fm.termin || "")))
      .map((x) => ({ soubor: x.f, termin: String(x.fm.termin).slice(0, 10), dni: dnyDo(x.fm.termin), kod: x.fm.kod || "" }))
      .sort((a, b) => a.dni - b.dni);
  }

  // ⏰ Úkoly do 3 dnů a po termínu – jednou denně (nebo hned na požádání)
  pripomenTerminy({ vzdy = false }) {
    const p = this.data.pripominky;
    const dnes = dnesniDatum();
    if (!vzdy && (!p.zapnuto || p.den === dnes)) return [];
    const blizko = this.ukolySTerminem().filter((u) => u.dni <= 3);
    if (!vzdy) { p.den = dnes; this.saveData(this.data); }
    if (!blizko.length) {
      if (vzdy) new Notice(T("⏰ V příštích 3 dnech žádný termín není."));
      return [];
    }
    const kdy = (u) => (u.dni < 0 ? T("{0} dní po termínu", -u.dni) : u.dni === 0 ? T("dnes") : u.dni === 1 ? T("zítra") : T("za {0} dní", u.dni));
    const frag = document.createDocumentFragment();
    frag.createDiv({ text: T("⏰ Blížící se termíny"), cls: "druhy-mozek-upozorneni-text" });
    for (const u of blizko.slice(0, 6)) frag.createDiv({ text: `${u.dni < 0 ? "⚠️" : "•"} ${u.kod ? u.kod + " · " : ""}${u.soubor.basename} – ${kdy(u)}` });
    const n = new Notice(frag, 20000);
    (n.containerEl || n.noticeEl)?.addEventListener("click", () => this.app.workspace.openLinkText(DOMOV, "", false));
    return blizko;
  }

  archivovane() {
    const a = this.app.vault.getAbstractFileByPath("_Archiv");
    return (a?.children || []).filter((c) => c.children && this.app.vault.getAbstractFileByPath(`_Archiv/${c.name}/${c.name}.md`)).map((c) => c.name).sort();
  }

  // 🗄 Konec semestru: předmět do _Archiv (nic se nemaže; zmizí z Domova, výběrů, plánu a fronty)
  async archivujPredmet(nazev) {
    const slozka = this.app.vault.getAbstractFileByPath(nazev);
    if (!slozka || nazev.includes("/") || /^[_.]/.test(nazev)) { new Notice(T("Předmět {0} nebyl nalezen.", nazev)); return false; }
    if (!this.app.vault.getAbstractFileByPath("_Archiv")) await this.app.vault.createFolder("_Archiv");
    if (this.app.vault.getAbstractFileByPath(`_Archiv/${nazev}`)) { new Notice(T("V archivu už předmět {0} je.", nazev)); return false; }
    await this.app.fileManager.renameFile(slozka, `_Archiv/${nazev}`);
    try { await this.spustPython("predmety.py", ["--css"]); } catch (e) { /* vzhled se opraví příště */ }
    new Notice(T("🗄 Předmět {0} je v archivu – zmizel z Domova, výběrů i plánu. Vrátit ho můžeš v Nastavení → Předměty.", nazev), 10000);
    return true;
  }

  async vratZArchivu(nazev) {
    const slozka = this.app.vault.getAbstractFileByPath(`_Archiv/${nazev}`);
    if (!slozka || nazev.includes("/")) return false;
    if (this.app.vault.getAbstractFileByPath(nazev)) { new Notice(T("Složka {0} už existuje – předmět nechávám v archivu.", nazev)); return false; }
    await this.app.fileManager.renameFile(slozka, nazev);
    try { await this.spustPython("predmety.py", ["--css"]); } catch (e) { /* vzhled se opraví příště */ }
    new Notice(T("↩️ Předmět {0} je zpět mezi předměty.", nazev));
    return true;
  }

  // 🃏 Kartičky „Otázka::Odpověď“ ze všech poznámek (bez šablon, archivu a systému)
  async nactiKarticky(predmet) {
    let vzor = "";
    try { vzor = (fs.readFileSync(path.join(this.zaklad, "_Systém", "Šablony", "Přednáška.md"), "utf8").match(/^.*::.*$/m) || [""])[0].trim(); } catch (e) { /* bez šablony */ }
    const karty = [], videne = new Set();
    const soubory = this.app.vault.getMarkdownFiles().filter((f) => !/^(_Systém|_Archiv)\//.test(f.path) && (!predmet || f.path.startsWith(predmet + "/")));
    for (const f of soubory) {
      const text = (await this.app.vault.cachedRead(f)).replace(/```[\s\S]*?```/g, "").replace(/`[^`\n]*`/g, "");  // ukázky v kódu nejsou kartičky
      for (const radek of text.split("\n")) {
        const r = radek.trim();
        if (!r.includes("::") || r === vzor || /^[#>|]/.test(r) || /\[[\w-]+::/.test(r)) continue;
        const m = /^(?:[-*+]\s+)?(.+?)\s*::\s*(.+)$/.exec(r);
        if (!m) continue;
        const id = crypto.createHash("sha1").update(m[1]).digest("hex").slice(0, 12);
        if (videne.has(id)) continue;
        videne.add(id);
        karty.push({ id, otazka: m[1], odpoved: m[2], soubor: f.path });
      }
    }
    return karty;
  }

  kartickaKOpakovani(k) {
    const z = this.data.karticky[k.id];
    return !z || z.d <= dnesniDatum();
  }

  async ohodnotKarticku(k, vim) {
    const z = this.data.karticky[k.id] || { b: 0 };
    const krabicka = vim ? Math.min((z.b || 0) + 1, KARTICKY_INTERVALY.length) : 0;
    this.data.karticky[k.id] = { b: krabicka, d: dnesniDatum(vim ? KARTICKY_INTERVALY[krabicka - 1] : 0) };
    await this.saveData(this.data);
  }

  // ---------- Aktualizace ----------

  async zkontrolujAktualizace({ automaticky }) {
    if (DISTRIBUCE === "obsidian") {  // verzi z adresáře aktualizuje Obsidian – žádné vlastní stahování
      if (!automaticky) new Notice(T("Druhý mozek z adresáře Obsidianu aktualizuje Obsidian: Nastavení → Pluginy třetích stran → Zkontrolovat aktualizace."), 10000);
      return null;
    }
    const a = this.data.aktualizace;
    if (automaticky && !a.kontrolovat) return null;
    try {
      const r = await requestUrl({ url: `https://api.github.com/repos/${REPOZITAR}/releases/latest`,
        headers: { Accept: "application/vnd.github+json" }, throw: false });
      a.posledni = new Date().toISOString();
      if (r.status === 404) {  // zatím žádné vydání
        a.nejnovejsi = null; a.chyba = null;
        await this.saveData(this.data);
        if (!automaticky) new Notice(T("✅ Máš nejnovější verzi ({0}).", this.verze()));
        return null;
      }
      if (r.status !== 200) throw new Error("HTTP " + r.status);
      const v = r.json || {};
      if (!VERZE.test(String(v.tag_name || ""))) throw new Error(T("neplatné číslo verze"));
      const zip = (v.assets || []).find((x) => /\.zip$/i.test(x?.name || ""));
      const stranka = odkazRepozitare(v.html_url) || `https://github.com/${REPOZITAR}/releases`;
      const zPopisu = zip ? new RegExp("`" + zip.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "`\\s*\\|\\s*`([0-9a-f]{64})`")
        .exec(String(v.body || "")) : null;
      const sha256 = /^sha256:([0-9a-f]{64})$/.exec(String(zip?.digest || ""))?.[1] || zPopisu?.[1] || null;
      a.nejnovejsi = { verze: String(v.tag_name).replace(/^v/, ""), stranka,
        zip: odkazRepozitare(zip?.browser_download_url) || stranka, sha256 };
      a.chyba = null;
      await this.saveData(this.data);
      if (novejsiVerze(a.nejnovejsi.verze, this.verze())) {
        if (!automaticky || this.odlozenaVerze !== a.nejnovejsi.verze) new AktualizaceModal(this, a.nejnovejsi).open();
      } else if (!automaticky) {
        new Notice(T("✅ Máš nejnovější verzi ({0}).", this.verze()));
      }
      return a.nejnovejsi;
    } catch (e) {
      a.chyba = e.message;
      await this.saveData(this.data);
      if (!automaticky) this.chyba(T("Novou verzi se nepodařilo zjistit: {0}", e.message), "aktualizace");
      return null;
    }
  }

  // Stáhne a ověří balík nové verze do dočasné složky. V trezoru se zatím nic nemění.
  async pripravAktualizaci(nova, krok, zruseno) {
    const odkaz = odkazRepozitare(nova.zip, "releases/download/");
    if (!odkaz) throw new Error(T("Odkaz ke stažení nevede na vydání tohoto projektu na GitHubu."));
    if (!nova.sha256) throw new Error(T("U vydání chybí kontrolní součet – aktualizuj ručně instalátorem."));
    krok("stahuji");
    const r = await requestUrl({ url: odkaz, throw: false });
    if (r.status !== 200) throw new Error(T("Stažení se nepovedlo (HTTP {0}).", r.status));
    const data = new Uint8Array(r.arrayBuffer);
    if (!data.length || data.length > MAX_BALIK) throw new Error(T("Stažený balík má nečekanou velikost."));
    if (zruseno()) return null;
    krok("overuji");
    if (crypto.createHash("sha256").update(data).digest("hex") !== nova.sha256)
      throw new Error(T("Kontrolní součet staženého balíčku nesouhlasí s GitHubem – instalace zastavena, nic se nezměnilo."));
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "druhy-mozek-aktualizace-"));
    const balik = { tmp, verze: nova.verze };
    try {
      fs.writeFileSync(path.join(tmp, "balik.zip"), data);
      await this.overObsahZipu(path.join(tmp, "balik.zip"));
      await spust("/usr/bin/ditto", ["-x", "-k", path.join(tmp, "balik.zip"), path.join(tmp, "rozbaleno")]);
      const slozky = fs.readdirSync(path.join(tmp, "rozbaleno")).map((n) => path.join(tmp, "rozbaleno", n))
        .filter((c) => fs.existsSync(path.join(c, "nastroje", "aktualizace.py")) && fs.existsSync(path.join(c, "SHA256SUMS.txt")));
      if (slozky.length !== 1) throw new Error(T("Balík nemá očekávanou podobu."));
      balik.koren = slozky[0];
      await spust("/usr/bin/shasum", ["-a", "256", "-c", "--quiet", "SHA256SUMS.txt"], { cwd: balik.koren });
      const uvedene = new Set(fs.readFileSync(path.join(balik.koren, "SHA256SUMS.txt"), "utf8").split("\n")
        .filter(Boolean).map((r) => r.slice(r.indexOf("  ") + 2).normalize("NFC")));
      const navic = souboryVeSlozce(balik.koren).map((r) => r.normalize("NFC"))
        .filter((r) => r !== "SHA256SUMS.txt" && !uvedene.has(r) && path.basename(r) !== ".DS_Store");
      if (navic.length) throw new Error(T("Balík obsahuje soubory, které nejsou v kontrolních součtech: {0}", navic.slice(0, 3).join(", ")));
      const manifest = JSON.parse(fs.readFileSync(path.join(balik.koren, "trezor", MANIFEST_ROZSIRENI), "utf8"));
      if (manifest.version !== nova.verze) throw new Error(T("Verze v balíčku ({0}) nesouhlasí s vydáním ({1}).", manifest.version, nova.verze));
      if (zruseno()) { this.uklidBalik(balik); return null; }
      krok("pripraveno");
      return balik;
    } catch (e) {
      this.uklidBalik(balik);
      throw e;
    }
  }

  // Před rozbalením: žádné absolutní cesty, „..“ ani symbolické odkazy (ochrana proti zápisu mimo dočasnou složku)
  async overObsahZipu(zip) {
    const jmena = (await spust("/usr/bin/zipinfo", ["-1", zip])).split("\n").filter(Boolean);
    if (!jmena.length || jmena.some((n) => n.startsWith("/") || n.split("/").includes("..")))
      throw new Error(T("Balík obsahuje nebezpečné cesty – instalace zastavena."));
    const vypis = (await spust("/usr/bin/zipinfo", [zip])).split("\n");
    if (vypis.some((r) => /^l[rwx-]{9}/.test(r)))
      throw new Error(T("Balík obsahuje symbolické odkazy – instalace zastavena."));
  }

  uklidBalik(balik) {
    try { if (balik?.tmp?.startsWith(os.tmpdir())) fs.rmSync(balik.tmp, { recursive: true, force: true }); } catch (e) { /* dočasná složka */ }
  }

  // Instalace ověřeného balíčku (jen po kliknutí na Instalovat)
  async instalujAktualizaci(balik) {
    try {
      if (this.data.zaloha?.zapnuto) await this.zalohuj({ tise: true });  // celá záloha trezoru předem
      const vystup = await spust(PYTHON, [path.join(balik.koren, "nastroje", "aktualizace.py"), "--cil", this.zaklad, "--json"]);
      const v = JSON.parse(vystup.trim().split("\n").pop());
      // klik na Instalovat potvrzuje jen soubory, které přesně odpovídají ověřenému balíčku; jiné změny dál hlídá 🛡
      this.data.otisky = this.data.otisky || {};
      const zdroj = path.join(balik.koren, "trezor");
      for (const rel of souboryVeSlozce(zdroj)) {
        const vTrezoru = path.join(this.zaklad, rel);
        if (fs.existsSync(vTrezoru) && otiskSouboru(vTrezoru) === otiskSouboru(path.join(zdroj, rel))) this.data.otisky[rel] = this.otisk(rel);
      }
      this.data.aktualizace.nejnovejsi = null;
      const skutecna = (c) => { try { return fs.realpathSync(c); } catch (e) { return path.resolve(c); } };
      const zaloha = skutecna(String(v.zaloha || ""));
      if ((v.nahrazeno.length || v.nove.length) && zaloha.startsWith(skutecna(path.join(this.zaklad, ".druhy-mozek-zaloha")) + path.sep)) {
        this.data.aktualizace.vratit = { slozka: path.basename(zaloha), z: v.puvodni, na: v.verze, nove: v.nove,
          nahrazeno: Object.fromEntries(v.nahrazeno.map((rel) => [rel, otiskSouboru(path.join(zaloha, rel))])) };
      }
      await this.saveData(this.data);
      new Notice(T("✅ Aktualizováno na verzi {0}.", v.verze) +
        (v.ponechano.length ? " " + T("Upravené soubory zůstaly, nová verze je vedle nich: {0}", v.ponechano.join(", ")) : "") +
        " " + T("Restartuj Obsidian, aby se načetla nová verze rozšíření."), 0);
      return v;
    } finally {
      this.uklidBalik(balik);
    }
  }

  // Poslední aktualizace, kterou jde vrátit – jen z vlastního záznamu rozšíření (ne ze souborů v trezoru, ty může kdokoli změnit)
  posledniAktualizace() {
    const a = this.data.aktualizace?.vratit;
    if (!a || !ZALOHA_VERZE.test(String(a.slozka)) || !fs.existsSync(path.join(this.zaklad, ".druhy-mozek-zaloha", a.slozka))) return null;
    return { ...a, nahrazeno: Object.keys(a.nahrazeno || {}), otisky: a.nahrazeno || {}, nove: a.nove || [] };
  }

  // ↩️ Vrátí soubory, které změnila poslední aktualizace (nic nemaže – nové soubory přesune do zálohy)
  async vratAktualizaci() {
    const a = this.posledniAktualizace();
    if (!a) throw new Error(T("Není co vracet."));
    const zaloha = path.join(this.zaklad, ".druhy-mozek-zaloha", a.slozka);
    // nejdřív ověřit VŠECHNO: záložní soubory musí být přesně ty, které aktualizace uložila, a nikam nesmí vést odkaz
    const mimoTrezor = (c) => { try { return fs.lstatSync(c).isSymbolicLink(); } catch (e) { return false; } };
    for (const rel of a.nahrazeno) {
      const z = path.join(zaloha, rel);
      if (!bezpecnaCesta(rel) || mimoTrezor(z) || mimoTrezor(path.join(this.zaklad, rel)) || !fs.existsSync(z) || otiskSouboru(z) !== a.otisky[rel])
        throw new Error(T("Záloha z aktualizace byla mezitím změněna ({0}) – z bezpečnostních důvodů nic nevracím.", rel));
    }
    for (const rel of a.nahrazeno) fs.copyFileSync(path.join(zaloha, rel), path.join(this.zaklad, rel));
    for (const rel of (a.nove || []).filter(bezpecnaCesta)) {
      const odkud = path.join(this.zaklad, rel), kam = path.join(zaloha, "_nove-z-aktualizace", rel);
      if (!fs.existsSync(odkud)) continue;
      fs.mkdirSync(path.dirname(kam), { recursive: true });
      fs.renameSync(odkud, kam);
    }
    this.data.aktualizace.vratit = null;
    try {  // evidence: vrácené soubory odpovídají předchozí verzi
      const ev = path.join(this.zaklad, "_Systém", "instalace.json");
      const e = JSON.parse(fs.readFileSync(ev, "utf8"));
      for (const rel of a.nahrazeno || []) e.soubory[rel] = this.otisk(rel);
      for (const rel of a.nove || []) delete e.soubory[rel];
      e.verze = a.z;
      fs.writeFileSync(ev, JSON.stringify(e, null, 1) + "\n");
    } catch (e) { /* evidence chybí – nevadí */ }
    // otisky se NEpotvrzují samy – vrácené soubory potvrdíš v 🛡 opsáním kódu
    await this.saveData(this.data);
    new Notice(T("↩️ Vráceno na verzi {0}. Na Domově potvrď 🛡 změny kódu.", a.z) + " " +
      T("Restartuj Obsidian, aby se načetla nová verze rozšíření."), 0);
    return a;
  }

  // ---------- Kontrola ----------
  // Názvy bodů se ukládají česky (klíče) a překládají až při zobrazení; podrobnosti se překládají hned.

  async kontrola({ automaticky }) {
    if (BALIK && !this.jeNastaveno()) return;
    const body = [];
    const bod = (nazev, stav, detail = "") => body.push({ nazev, stav, detail });
    const pluginy = this.app.plugins;
    const manifest = pluginy.manifests[ROADMAP_ID];
    const verze = manifest?.version || null;
    const nr = pluginy.plugins[ROADMAP_ID];
    let ulozitNastaveni = false;

    // Neuro Roadmap je volitelný: když ho někdo nemá, není to chyba – jen když ho měl a teď chybí
    if (!manifest) bod("Plugin Neuro Roadmap", this.data.posledniVerze ? "varovani" : "ok",
      this.data.posledniVerze ? T("Byl nainstalovaný, teď chybí – plánování úkolů nefunguje.")
        : T("volitelný – nenainstalovaný (plánování: Nastavení → Pluginy třetích stran → Neuro Roadmap)"));
    else if (!pluginy.enabledPlugins.has(ROADMAP_ID) || !nr) bod("Plugin Neuro Roadmap", "varovani", T("Je vypnutý – zapni ho v Nastavení → Pluginy třetích stran."));
    else bod("Plugin Neuro Roadmap", "ok", T("verze {0}", verze));

    if (nr) {
      // 1) příkaz pro otevření plánu
      const prikazy = this.app.commands.commands;
      if (prikazy[this.data.roadmapPrikaz]) bod("Tlačítko 🧭 Plán úkolů", "ok");
      else {
        const nahrada = Object.keys(prikazy).find((id) => id.startsWith(ROADMAP_ID + ":") && /open|roadmap|dashboard/i.test(id));
        if (nahrada) { this.data.roadmapPrikaz = nahrada; bod("Tlačítko 🧭 Plán úkolů", "opraveno", T("příkaz se přejmenoval na {0}", nahrada)); }
        else bod("Tlačítko 🧭 Plán úkolů", "chyba", T("Plugin už nemá příkaz pro otevření plánu."));
      }

      // 2) vlastnosti systému a jejich hodnoty v jeho nastavení
      const s = nr.settings;
      if (!s || typeof s.propertyMappings !== "object" || typeof s.valueMappings !== "object") {
        bod("Vlastnosti systému (kod, termin, stav, typ)", "chyba", T("Změnila se struktura nastavení pluginu – nejde doplnit automaticky."));
      } else {
        const doplneno = [], neznamo = [];
        for (const [mapa, pravidla] of [[s.propertyMappings, MAPOVANI_VLASTNOSTI], [s.valueMappings, MAPOVANI_HODNOT]]) {
          for (const [klic, pridat] of Object.entries(pravidla)) {
            if (!(klic in mapa)) { neznamo.push(klic); continue; }
            const { hodnota, chybi } = doplnSeznam(mapa[klic], pridat);
            if (chybi.length) { mapa[klic] = hodnota; doplneno.push(`${klic}: ${chybi.join(", ")}`); }
          }
        }
        if (doplneno.length) ulozitNastaveni = true;
        if (neznamo.length) bod("Vlastnosti systému (kod, termin, stav, typ)", "varovani", T("Plugin už nezná položky: {0}", neznamo.join(", ")));
        else if (doplneno.length) bod("Vlastnosti systému (kod, termin, stav, typ)", "opraveno", T("znovu doplněno – {0}", doplneno.join("; ")));
        else bod("Vlastnosti systému (kod, termin, stav, typ)", "ok");
      }

      // 3) vyloučené systémové složky (šablony nesmí být úkoly)
      if (s && "excludedPathPrefixes" in s) {
        const { hodnota, chybi } = doplnSeznam(s.excludedPathPrefixes, VYLOUCENE_SLOZKY.join(", "));
        if (chybi.length) { s.excludedPathPrefixes = hodnota; ulozitNastaveni = true; bod("Vyloučení složky _Systém", "opraveno", T("znovu nastaveno")); }
        else bod("Vyloučení složky _Systém", "ok");
      } else bod("Vyloučení složky _Systém", "varovani", T("Plugin už nemá nastavení vyloučených složek."));

      if (ulozitNastaveni) {
        try {
          if (typeof nr.saveSettings === "function") await nr.saveSettings(); else await nr.saveData(s);
          await new Promise((ok) => setTimeout(ok, 1500)); // nech plugin přeindexovat
        } catch (e) {
          bod("Uložení oprav do nastavení", "chyba", e.message);
        }
      }

      // 4) funkční test: vidí plugin naše otevřené úkoly se správným předmětem a termínem?
      const ukoly = this.app.vault.getMarkdownFiles()
        .map((f) => ({ f, fm: this.app.metadataCache.getFileCache(f)?.frontmatter }))
        .filter((x) => x.fm?.typ === "ukol" && x.fm?.stav !== "hotovo" && !x.f.path.startsWith("_Systém/"));
      if (typeof nr.indexer?.getSnapshot !== "function") {
        bod("Úkoly v plánu", "varovani", T("Plugin změnil vnitřní rozhraní – úkoly nejde automaticky ověřit, zkontroluj je v plánu ručně."));
      } else if (!ukoly.length) {
        bod("Úkoly v plánu", "ok", T("zatím žádný otevřený úkol k ověření"));
      } else {
        try {
          const snimek = await nr.indexer.getSnapshot();
          const uzly = Array.isArray(snimek) ? snimek : snimek?.nodes || snimek?.tasks || [];
          const spatne = ukoly.filter(({ f, fm }) => {
            const u = uzly.find((n) => n.path === f.path && (n.source === "frontmatter" || n.title === f.basename));
            return !u || (fm.kod && u.subject !== String(fm.kod)) || (fm.termin && String(u.dueDate || u.due || "") !== String(fm.termin));
          });
          if (spatne.length) bod("Úkoly v plánu", "chyba", T("Plugin nečte správně {0} z {1} úkolů: {2}", spatne.length, ukoly.length, spatne.map((x) => x.f.basename).join(", ")));
          else bod("Úkoly v plánu", "ok", T("všech {0} otevřených úkolů má správný předmět i termín", ukoly.length));
        } catch (e) {
          bod("Úkoly v plánu", "varovani", T("Ověření selhalo: {0}", e.message));
        }
      }
    }

    // 5) integrita kódu – nezměnil někdo skripty, rozšíření, překlady nebo pravidla pro AI?
    const zmenene = this.zmeneneSoubory();
    if (zmenene === null) bod("Integrita kódu", "ok", T("výchozí stav uložen"));
    else if (zmenene.length) bod("Integrita kódu", "varovani", T("Změnily se: {0}. Pokud jsi to nebyl ty (nebo AI na tvůj pokyn), nic nepotvrzuj a ozvi se. Jinak klikni na 🛡 Potvrdit změny kódu. Do potvrzení se skripty z Obsidianu nespouští.", zmenene.join(", ")));
    else bod("Integrita kódu", "ok", T("{0} chráněných souborů beze změny", CHRANENE.length));

    // 6) automatická záloha
    const z = this.data.zaloha;
    if (!z.zapnuto) bod("Automatická záloha", "varovani", T("Je vypnutá – zapni ji v Nastavení → Second Brain for KISK."));
    else if (!z.slozka) bod("Automatická záloha", "varovani", T("Není nastavená složka zálohy (cloud nenalezen) – nastav ji v Nastavení → Second Brain for KISK."));
    else if (z.chyba) bod("Automatická záloha", "chyba", T("Poslední záloha selhala: {0}", z.chyba));
    else if (!z.posledni) bod("Automatická záloha", "ok", T("první záloha proběhne do minuty → {0}", z.slozka));
    else if (Date.now() - Date.parse(z.posledni) > 3 * ZALOHA_DENNE_MS) bod("Automatická záloha", "varovani", T("Poslední záloha je starší než 3 dny."));
    else bod("Automatická záloha", "ok", T("poslední {0} → {1}", kdy(z.posledni), z.slozka));

    // 7) naše vlastní části
    const chybiSoubory = SOUBORY_SYSTEMU.filter((p) => !fs.existsSync(path.join(this.zaklad, p)));
    if (!fs.existsSync(PYTHON)) bod("Python (fronta, šablona Word)", "chyba", T("Nenalezen {0}", PYTHON));
    else if (chybiSoubory.length) bod("Soubory druhého mozku", "chyba", T("Chybí: {0}", chybiSoubory.join(", ")));
    else bod("Soubory druhého mozku a Python", "ok");
    const rezim = this.rezimAI();
    if (rezim === "claude") bod("AI: Claude Code", fs.existsSync(CLAUDE) ? "ok" : "varovani", fs.existsSync(CLAUDE) ? "" : T("Nenalezen {0}", CLAUDE));
    else if (rezim === "jina") {
      const sablona = String(this.nastaveni().ai_prikaz || "");
      bod("AI: jiná", BEZPECNY_AI_PRIKAZ.test(sablona) ? "ok" : "chyba",
        BEZPECNY_AI_PRIKAZ.test(sablona) ? sablona : T("Neplatný ai_prikaz v nastaveni.json (musí obsahovat {prompt}, bez zvláštních znaků)."));
    } else bod("AI", "ok", T("vypnutá – ruční režim"));

    // vyhodnocení
    const celkem = body.some((b) => b.stav === "chyba") ? "chyba" : body.some((b) => b.stav === "varovani") ? "varovani"
      : body.some((b) => b.stav === "opraveno") ? "opraveno" : "ok";
    const zmenaVerze = verze && this.data.posledniVerze && verze !== this.data.posledniVerze;
    const predchozi = this.data.posledniVerze;
    const puvodniStav = this.data.kontrola?.celkem;
    this.data.kontrola = { celkem, verze, predchozi: zmenaVerze ? predchozi : null, cas: new Date().toISOString(), body };
    if (verze) this.data.posledniVerze = verze;
    await this.saveData(this.data);

    if (!automaticky || zmenaVerze || celkem !== "ok" || puvodniStav !== celkem) await this.zapisZpravu();
    this.aktualizujStavovyRadek();
    this.prekresliStav();
    this.upozorni({ celkem, verze, predchozi, zmenaVerze, automaticky });
  }

  otisk(rel) {
    try {
      return crypto.createHash("sha256").update(fs.readFileSync(path.join(this.zaklad, rel))).digest("hex");
    } catch (e) {
      return "chybí";
    }
  }

  // null = první spuštění (uloží výchozí stav), jinak seznam změněných souborů
  zmeneneSoubory() {
    if (!this.data.otisky) {
      this.data.otisky = Object.fromEntries(CHRANENE.map((p) => [p, this.otisk(p)]));
      return null;
    }
    return CHRANENE.filter((p) => this.data.otisky[p] !== this.otisk(p));
  }

  // Potvrzení změn kódu jde jen kliknutím člověka v okně – příkaz ani skript ho neprovede sám
  potvrdIntegritu() {
    const zmenene = this.zmeneneSoubory() || [];
    if (!zmenene.length) { new Notice(T("🛡 Žádné nepotvrzené změny.")); return; }
    new PotvrzeniModal(this, zmenene).open();
  }

  async ulozIntegritu(zmenene) {
    this.data.otisky = Object.fromEntries(CHRANENE.map((p) => [p, this.otisk(p)]));
    await this.saveData(this.data);
    new Notice(T("🛡 Potvrzeno: {0}", zmenene.join(", ")), 8000);
    await this.kontrola({ automaticky: false });
    if (this.data.zaloha.zapnuto) this.zalohuj({ tise: true });
  }

  // Obnoví otisky jen u zadaných souborů (po změně provedené kliknutím v nastavení)
  async obnovOtisky(soubory) {
    if (!this.data.otisky) return;
    for (const p of soubory) this.data.otisky[p] = this.otisk(p);
    await this.saveData(this.data);
  }

  // ---------- Automatická záloha ----------

  // Místa, kam jde zálohovat (zobrazí se v nastavení); typ: cloud / lokalni / disk
  mistaZalohy() {
    const domov = os.homedir(), mista = [];
    try {
      const cloud = path.join(domov, "Library", "CloudStorage");
      for (const d of fs.readdirSync(cloud).filter((x) => x.startsWith("OneDrive")).sort())
        mista.push({ typ: "cloud", nazev: `OneDrive (${d.replace(/^OneDrive-?/, "") || T("osobní")})`, cesta: path.join(cloud, d, "Záloha", "Druhý mozek") });
      // Google Drive pro počítač: CloudStorage/GoogleDrive-<účet>/My Drive (česky „Můj disk“)
      for (const d of fs.readdirSync(cloud).filter((x) => x.startsWith("GoogleDrive")).sort()) {
        const disk = ["My Drive", "Můj disk"].map((n) => path.join(cloud, d, n)).find((c) => fs.existsSync(c));
        if (disk) mista.push({ typ: "cloud", nazev: `Google Drive (${d.replace(/^GoogleDrive-?/, "")})`, cesta: path.join(disk, "Záloha", "Druhý mozek") });
      }
      for (const d of fs.readdirSync(cloud).filter((x) => x.startsWith("Dropbox")).sort())
        mista.push({ typ: "cloud", nazev: "Dropbox", cesta: path.join(cloud, d, "Záloha", "Druhý mozek") });
    } catch (e) { /* bez cloudových úložišť */ }
    const icloud = path.join(domov, "Library", "Mobile Documents", "com~apple~CloudDocs");
    if (fs.existsSync(icloud)) mista.push({ typ: "cloud", nazev: "iCloud Drive", cesta: path.join(icloud, "Záloha", "Druhý mozek") });
    mista.push({ typ: "lokalni", nazev: T("Dokumenty (jen v tomto Macu)"), cesta: path.join(domov, "Documents", "Záloha", "Druhý mozek") });
    try {
      for (const v of fs.readdirSync("/Volumes")) {
        const kde = path.join("/Volumes", v);
        if (fs.realpathSync(kde) !== "/") mista.push({ typ: "disk", nazev: T("Externí disk: {0}", v), cesta: path.join(kde, "Záloha", "Druhý mozek") });
      }
    } catch (e) { /* bez disků */ }
    return mista;
  }

  // Výchozí místo: první cloud (OneDrive → Google Drive → Dropbox → iCloud); bez cloudu prázdné
  vychoziSlozkaZalohy() {
    const cloud = this.mistaZalohy().find((m) => m.typ === "cloud");
    return cloud ? cloud.cesta : "";
  }

  naplanujZalohu() {
    if (!this.data.zaloha.zapnuto) return;
    clearTimeout(this.casovacZalohy);
    this.casovacZalohy = setTimeout(() => this.zalohuj({ tise: true }), ZALOHA_PO_ZMENE_MS);
  }

  zahrnoutDoZalohy(rel) {
    if (!rel) return true;
    if (ZALOHA_VZDY.includes(rel)) return true;
    if (ZALOHA_VYNECHAT.some((v) => rel === v || rel.startsWith(v + "/"))) return false;
    const jmeno = path.basename(rel);
    if (jmeno === ".DS_Store" || jmeno.startsWith(".priprav") || jmeno.startsWith("~$")) return false;
    const prefix = this.vlastniPrefix();
    if (prefix && jmeno.startsWith(prefix)) return true;  // vlastní práce zálohujeme vždy
    return this.data.zaloha.materialy || !MATERIAL.test(jmeno);
  }

  async zalohuj({ tise }) {
    const z = this.data.zaloha;
    clearTimeout(this.casovacZalohy);
    if (!z.slozka) { if (!tise) new Notice(T("💾 Není nastavená složka zálohy – nastav ji v Nastavení → Second Brain for KISK."), 10000); return false; }
    if (this.zalohujeSe) return false;
    this.zalohujeSe = true;
    const koren = path.resolve(z.slozka);
    const d = new Date(), dv = (n) => String(n).padStart(2, "0");
    let nazev = `${d.getFullYear()}-${dv(d.getMonth() + 1)}-${dv(d.getDate())} ${dv(d.getHours())}.${dv(d.getMinutes())}`;
    try {
      fs.mkdirSync(koren, { recursive: true });
      if (fs.existsSync(path.join(koren, nazev))) nazev += `.${dv(d.getSeconds())}`;
      const docasna = path.join(koren, ".probiha-" + nazev);
      const cil = path.join(koren, nazev);
      fs.cpSync(this.zaklad, path.join(docasna, "Trezor"), {
        recursive: true,
        filter: (zdroj) => this.zahrnoutDoZalohy(path.relative(this.zaklad, zdroj).split(path.sep).join("/")),
      });
      fs.renameSync(docasna, cil);
      fs.writeFileSync(path.join(koren, "OBNOVA – přečti mě.md"), [
        T("# Automatické zálohy druhého mozku"), "",
        T("Každá složka s datem je jedna záloha (uchovává se posledních {0}). Nejnovější je dole.", z.pocet), "",
        T("## Obnova"), T("1. Otevři nejnovější složku → `Trezor`."),
        T("2. Zkopíruj její obsah do složky trezoru (skryté `.obsidian` a `.claude` zobrazíš ve Finderu přes Cmd+Shift+.)."),
        z.materialy ? T("   Záloha obsahuje i studijní materiály.") : T("   Originály materiálů nech, kde jsou – záloha obsahuje jen poznámky, systém a vlastní práce."),
        T("3. V Obsidianu klikni na 🩺 Zkontrolovat propojení; když hlásí 🛡 Integrita kódu, potvrď změny opsáním kódu."), "",
        T("Nastavení zálohy: Obsidian → Nastavení → Second Brain for KISK → Automatická záloha."), "",
      ].join("\n"));
      // rotace: smaže jen nejstarší složky se zálohami (podle názvu s datem) uvnitř složky záloh
      const verze = fs.readdirSync(koren).filter((n) => ZALOHA_VERZE.test(n)).sort();
      for (const stara of verze.slice(0, Math.max(0, verze.length - Math.max(1, z.pocet)))) {
        const cesta = path.join(koren, stara);
        if (path.dirname(cesta) === koren) fs.rmSync(cesta, { recursive: true, force: true });
      }
      z.posledni = new Date().toISOString();
      z.chyba = null;
      if (!tise) new Notice(T("💾 Záloha hotová: {0}", nazev), 6000);
      await this.uklidZalohyAktualizace();
      return true;
    } catch (e) {
      z.chyba = e.message;
      this.chyba(T("💾 Záloha se nepodařila: {0}", e.message), "zaloha");
      return false;
    } finally {
      this.zalohujeSe = false;
      await this.saveData(this.data);
    }
  }

  pocetZaloh(koren) {
    try {
      return fs.readdirSync(koren).filter((n) => ZALOHA_VERZE.test(n)).length;
    } catch (e) {
      return 0;
    }
  }

  // Smaže jen naše zálohy (složky s datem, rozpracované a návod) – nic jiného ve složce
  smazStareZalohy(koren) {
    koren = path.resolve(koren);
    let smazano = 0;
    for (const n of fs.readdirSync(koren)) {
      if (ZALOHA_VERZE.test(n) || n.startsWith(".probiha-") || n === "OBNOVA – přečti mě.md") {
        fs.rmSync(path.join(koren, n), { recursive: true, force: true });
        smazano++;
      }
    }
    if (fs.readdirSync(koren).filter((n) => n !== ".DS_Store").length === 0) fs.rmSync(koren, { recursive: true, force: true });
    return smazano;
  }

  // Dočasná záloha z aktualizace (.druhy-mozek-zaloha) jde do koše, až když aktualizace funguje:
  // běží nová verze rozšíření, změny kódu jsou potvrzené (🛡) a právě proběhla úspěšná záloha s novou verzí.
  async uklidZalohyAktualizace() {
    try {
      const slozka = path.join(this.zaklad, ".druhy-mozek-zaloha");
      if (!fs.existsSync(slozka)) return 0;
      const zmenene = this.zmeneneSoubory();
      if (!zmenene || zmenene.length) return 0;  // změny kódu ještě nejsou potvrzené
      let uklizeno = 0;
      const hranice = Date.now() - ZALOHA_AKTUALIZACE_DNI * 24 * 60 * 60 * 1000;
      const datum = (n) => Date.parse(n.slice(0, 10) + "T" + n.slice(11, 16).replace(".", ":"));
      for (const n of fs.readdirSync(slozka).filter((x) => ZALOHA_VERZE.test(x) && datum(x) < hranice)) {
        if (!(await this.app.vault.adapter.trashSystem(`.druhy-mozek-zaloha/${n}`))) break;
        uklizeno++;
      }
      if (uklizeno) new Notice(T("🧹 Aktualizace je potvrzená a zazálohovaná – dočasná záloha z aktualizace je v koši."), 8000);
      return uklizeno;
    } catch (e) {
      return 0;  // nevadí, zkusí se to při další záloze
    }
  }

  async zmenSlozkuZalohy(nova, smazatStare) {
    const z = this.data.zaloha, stara = z.slozka;
    z.slozka = nova;
    await this.saveData(this.data);
    const povedlo = await this.zalohuj({ tise: false });
    if (smazatStare && stara && path.resolve(stara) !== path.resolve(nova)) {
      if (!povedlo) { new Notice(T("💾 Nová záloha se nepovedla – staré zálohy jsem NEsmazala."), 12000); return; }
      try {
        new Notice(T("🧹 Staré zálohy smazány ({0}) z: {1}", this.smazStareZalohy(stara), stara), 10000);
      } catch (e) {
        this.chyba(T("Staré zálohy se nepodařilo smazat: {0}", e.message), "zaloha");
      }
    }
  }

  // ---------- Upozornění, stav, zpráva ----------

  upozorni({ celkem, verze, predchozi, zmenaVerze, automaticky }) {
    const uvod = zmenaVerze ? T("Neuro Roadmap se aktualizoval ({0} → {1}). ", predchozi, verze) : "";
    // vždy jen jedno upozornění z kontroly – nové nahradí staré, aby se nehromadila
    this.posledniUpozorneni?.hide();
    this.posledniUpozorneni = null;
    if (celkem === "ok") {
      if (zmenaVerze || !automaticky) this.posledniUpozorneni = new Notice(T("🧠✅ {0}Kontrola druhého mozku: vše funguje.", uvod), 8000);
      return;
    }
    const frag = document.createDocumentFragment();
    const text = {
      opraveno: T("🧠🔧 {0}Něco se rozbilo, ale opravilo se to samo. Podrobnosti v Kontrole.", uvod),
      varovani: T("🧠⚠️ {0}Kontrola druhého mozku hlásí varování. Klikni pro podrobnosti.", uvod),
      chyba: T("🧠❌ {0}Kontrola druhého mozku hlásí chybu. Klikni pro podrobnosti a opravu.", uvod),
    }[celkem];
    frag.createDiv({ text, cls: "druhy-mozek-upozorneni-text" });
    const zavrit = frag.createEl("button", { text: "×", cls: "druhy-mozek-zavrit", attr: { "aria-label": T("Zavřít") } });
    const n = new Notice(frag, celkem === "opraveno" ? 12000 : 0);
    // × zavře upozornění bez otevírání zprávy, klik jinam otevře podrobnosti
    zavrit.addEventListener("click", (e) => { e.stopPropagation(); n.hide(); });
    const el = n.containerEl || n.noticeEl;
    el?.addClass("druhy-mozek-upozorneni", "is-" + celkem);
    el?.addEventListener("click", () => this.app.workspace.openLinkText(ZPRAVA, "", true));
    this.posledniUpozorneni = n;
  }

  ikonaStavu(celkem) {
    return { ok: "✅", opraveno: "🔧", varovani: "⚠️", chyba: "❌" }[celkem] || "…";
  }

  nazevStavu(celkem) {
    return { ok: T("v pořádku"), opraveno: T("opraveno"), varovani: T("varování"), chyba: T("chyba") }[celkem] || celkem;
  }

  aktualizujStavovyRadek() {
    const k = this.data.kontrola;
    this.stavovyRadek.setText(T("🧠 {0} Kontrola", k ? this.ikonaStavu(k.celkem) : "…"));
    this.stavovyRadek.setAttr("aria-label", k ? T("Kontrola druhého mozku: {0} – klikni pro podrobnosti", this.nazevStavu(k.celkem)) : T("Kontrola ještě neproběhla"));
    this.stavovyRadek.toggleClass("is-problem", !!k && (k.celkem === "chyba" || k.celkem === "varovani"));
  }

  vykresliStav(el) {
    el.empty();
    const k = this.data.kontrola;
    const box = el.createDiv({ cls: "druhy-mozek-banner is-" + (k?.celkem || "neznamo") });
    if (!k) { box.setText(T("🧠 Kontrola druhého mozku ještě neproběhla.")); return; }
    const popis = {
      ok: T("Vše funguje"),
      opraveno: T("Něco se rozbilo, ale opravilo se to samo"),
      varovani: T("Něco vyžaduje pozornost"),
      chyba: T("Něco nefunguje"),
    }[k.celkem];
    box.createSpan({ text: `${this.ikonaStavu(k.celkem)} ${popis} · ${T("kontrola {0}", kdy(k.cas, true))}` });
    if (k.celkem !== "ok") {
      const problemy = k.body.filter((b) => b.stav !== "ok");
      const ul = box.createEl("ul");
      for (const b of problemy) ul.createEl("li", { text: `${this.ikonaStavu(b.stav)} ${T(b.nazev)}${b.detail ? " – " + b.detail : ""}` });
      const tl = box.createDiv({ cls: "druhy-mozek-tlacitka" });
      tl.createEl("button", { text: T("🩺 Zkontrolovat znovu") }).addEventListener("click", () => this.kontrola({ automaticky: false }));
      if (problemy.some((b) => b.nazev === "Integrita kódu"))
        tl.createEl("button", { text: T("🛡 Změny kódu byly moje – potvrdit") }).addEventListener("click", () => this.potvrdIntegritu());
      if (problemy.some((b) => b.nazev !== "Integrita kódu") && this.rezimAI() !== "zadna")
        tl.createEl("button", { text: T("🔧 Nechat AI opravit") }).addEventListener("click", () => this.claude("/oprav-roadmap"));
    }
  }

  prekresliStav() {
    // bannery se překreslí na místě – funguje v režimu čtení i úprav
    for (const el of [...this.bannery]) {
      if (el.isConnected) this.vykresliStav(el); else this.bannery.delete(el);
    }
  }

  async zapisZpravu() {
    const k = this.data.kontrola;
    const radky = [
      T("# 🩺 Kontrola druhého mozku"), "",
      T("**Výsledek:** {0} {1} · **Neuro Roadmap:** {2}", this.ikonaStavu(k.celkem), this.nazevStavu(k.celkem), k.verze || "—")
        + (k.predchozi ? T(" (předtím {0})", k.predchozi) : ""),
      T("**Zkontrolováno:** {0}", kdy(k.cas)), "",
      T("| | Kontrola | Podrobnosti |"), "|---|---|---|",
      ...k.body.map((b) => `| ${this.ikonaStavu(b.stav)} | ${T(b.nazev)} | ${(b.detail || "").replace(/\|/g, "/")} |`), "",
      T("## Co dělat"),
      T("- ✅ / 🔧 – nic, vše funguje (🔧 = opraveno automaticky)."),
      T("- 🛡 Integrita kódu ⚠️ – změnil se skript nebo pravidla pro AI. Když to byla tvoje (nebo AI na tvůj pokyn) úprava, klikni na **🛡 Potvrdit změny kódu**."),
      T("  Když nevíš, odkud změna je, NEPOTVRZUJ ji – skripty se do potvrzení nespustí."),
      T("- ⚠️ / ❌ u Neuro Roadmap – na Domově klikni na **🔧 Nechat AI opravit**."),
      T("  AI si přečte tuhle zprávu a novou dokumentaci pluginu a upraví naše propojení."),
      T("- 💾 Záloha ⚠️ / ❌ – zkontroluj Nastavení → Second Brain for KISK → Automatická záloha."),
      "", T("*Kontrola běží sama při spuštění Obsidianu a každých 6 hodin; ručně přes 🩺 Zkontrolovat propojení.*"),
    ];
    const f = this.app.vault.getAbstractFileByPath(ZPRAVA);
    if (f instanceof TFile) await this.app.vault.modify(f, radky.join("\n") + "\n");
    else await this.app.vault.create(ZPRAVA, radky.join("\n") + "\n");
  }

  ukazMenu(evt) {
    const menu = new Menu();
    for (const a of this.akce()) menu.addItem((i) => i.setTitle(a.nazev).setIcon(a.ikona).onClick(a.spust));
    menu.showAtMouseEvent(evt);
  }

  vykresliTlacitka(zdroj, el) {
    const vybrane = zdroj.split(/\s+/).filter(Boolean);
    const bezAI = this.rezimAI() === "zadna";
    const akce = this.akce().filter((a) => (!vybrane.length || vybrane.includes(a.id)) && !(a.jenRucne && !bezAI));
    const box = el.createDiv({ cls: "druhy-mozek-tlacitka" });
    for (const a of akce) {
      const b = box.createEl("button", { text: a.nazev });
      b.addEventListener("click", a.spust);
    }
  }

  // ---------- Nastavení ----------

  otevriNastaveni() {
    this.app.setting.open();
    this.app.setting.openTabById(this.manifest.id);
  }

  // Zápis z okna nastavení (jen kliknutím člověka) – soubor je chráněný, proto rovnou obnoví jeho otisk
  async ulozNastaveni(nove, puvodni) {
    const zmenaJazyka = (puvodni.jazyk || "cs") !== (nove.jazyk || "cs");
    const zmenaSablony = ["jmeno", "uco", "jazyk", "jazyk_word"].some((x) => (puvodni[x] || "") !== (nove[x] || ""));
    if (zmenaJazyka && this.data.zaloha.zapnuto) await this.zalohuj({ tise: true });  // záloha před přepsáním systémových poznámek

    fs.writeFileSync(path.join(this.zaklad, "_Systém", "nastaveni.json"), JSON.stringify(nove, null, 2) + "\n");
    await this.obnovOtisky(["_Systém/nastaveni.json"]);
    this.nactiJazyk();

    // vše shrnuté do jednoho upozornění (dřív jich po uložení vyskočilo několik)
    const zpravy = [T("⚙️ Nastavení uloženo.")];
    let chyba = false;
    if (zmenaJazyka) {
      try {
        const n = await this.aplikujJazykovyBalicek(nove.jazyk || "cs");
        zpravy.push(T("🌐 Jazyk přepnut – systémové poznámky přeloženy ({0}). Tvoje poznámky se nezměnily.", n));
      } catch (e) {
        zpravy.push(T("Jazykový balíček se nepodařilo použít: {0}", e.message)); chyba = true;
      }
    }
    if (zmenaSablony) {
      try {
        await this.spustPython("Word/vytvor_sablonu.py", []);
        zpravy.push(T("📝 Šablona Wordu přegenerována."));
      } catch (e) {
        zpravy.push(T("Šablonu Wordu se nepodařilo přegenerovat: {0}", e.message)); chyba = true;
      }
    }
    for (const leaf of this.app.workspace.getLeavesOfType("markdown")) leaf.view?.previewMode?.rerender(true);
    new Notice(zpravy.join("\n"), chyba ? 12000 : 6000);
    await this.kontrola({ automaticky: true });  // ozve se jen při problému
    if (this.data.zaloha.zapnuto) this.zalohuj({ tise: true });
    if (zmenaJazyka) this.registrujPrikazy();  // aby se přeložily i názvy příkazů
  }

  nastaveni() {
    try {
      return JSON.parse(fs.readFileSync(path.join(this.zaklad, "_Systém", "nastaveni.json"), "utf8"));
    } catch (e) {
      return {};
    }
  }

  // "claude" (výchozí) | "jina" (vlastní příkaz v Terminálu) | "zadna" (ruční režim)
  rezimAI() {
    const r = this.nastaveni().ai;
    return ["claude", "jina", "zadna"].includes(r) ? r : "claude";
  }

  vlastniPrefix() {
    const n = this.nastaveni();
    return n.uco ? `${n.uco}-${n.jmeno_soubor}` : null;
  }

  predmety() {
    return this.app.vault.getMarkdownFiles()
      .map((f) => ({ f, fm: this.app.metadataCache.getFileCache(f)?.frontmatter }))
      .filter((x) => x.fm?.typ === "predmet" && !x.f.path.startsWith("_Systém/") && !x.f.path.startsWith("_Archiv/"))
      .map((x) => ({ nazev: x.f.basename, kod: x.fm.kod || "", soubor: x.f }))
      .sort((a, b) => String(a.kod).localeCompare(String(b.kod)));
  }

  // ---------- Skripty a AI ----------

  spustPython(skript, argumenty) {
    const rel = "_Systém/" + skript;
    if (this.data.otisky && this.data.otisky[rel] && this.data.otisky[rel] !== this.otisk(rel)) {
      new Notice(T("🛡 Skript {0} se změnil a změna nebyla potvrzena – z bezpečnostních důvodů ho nespustím. Otevři 🩺 Kontrolu a změnu zkontroluj.", skript), 0);
      this.kontrola({ automaticky: false });
      return Promise.reject(new Error(T("nepotvrzená změna skriptu")));
    }
    return new Promise((ok, chyba) => {
      execFile(PYTHON, [path.join("_Systém", skript), ...argumenty], { cwd: this.zaklad, timeout: 300000 },
        (err, stdout, stderr) => (err ? chyba(new Error((stderr || err.message).trim())) : ok(stdout.trim())));
    });
  }

  naplanujFrontu() {
    clearTimeout(this.casovacFronty);
    this.casovacFronty = setTimeout(() => this.spustPython("priprav.py", []).catch(() => {}), 4000);
  }

  async ukazFrontu() {
    try {
      const vystup = await this.spustPython("priprav.py", []);
      new Notice(vystup.split("\n").slice(0, 2).join("\n"), 8000);
      await this.app.workspace.openLinkText(FRONTA, "", true);
    } catch (e) {
      this.chyba(T("Fronta se nepodařila spočítat: {0}", e.message), "fronta");
    }
  }

  // Sestaví příkaz pro Terminál podle režimu AI; null = nejde spustit
  claudePrikaz(prikaz) {
    const rezim = this.rezimAI();
    let ai;
    if (rezim === "claude") {
      ai = `claude --model sonnet --permission-mode acceptEdits ${shellUvozovky(prikaz)}`;
    } else if (rezim === "jina") {
      const sablona = String(this.nastaveni().ai_prikaz || "");
      if (!BEZPECNY_AI_PRIKAZ.test(sablona)) return null;
      const [, jmeno, arg] = prikaz.match(/^\/(\S+)\s*(.*)$/) || [];
      const zadani = `Postupuj přesně podle souboru .claude/commands/${jmeno}.md a pravidel v .claude/CLAUDE.md ` +
        "(včetně bezpečnostních pravidel – platí i pro tebe)." + (arg ? ` Předmět: ${arg}.` : "");
      ai = sablona.replace("{prompt}", shellUvozovky(zadani));
    } else {
      return null;
    }
    const shell = `cd ${shellUvozovky(this.zaklad)} && clear && ${ai}`;
    return `tell application "Terminal"\nactivate\ndo script ${asUvozovky(shell)}\nend tell`;
  }

  claude(prikaz) {
    const rezim = this.rezimAI();
    if (rezim === "zadna") { new Notice(T("AI je vypnutá (ruční režim) – viz 01 Návod, kapitola Práce s AI.")); return; }
    const skript = this.claudePrikaz(prikaz);
    if (!skript) {
      new Notice(T("Příkaz jiné AI v _Systém/nastaveni.json je neplatný – musí obsahovat {prompt} a jen písmena, čísla, mezery a . _ / = : -"), 12000);
      return;
    }
    execFile("osascript", ["-e", skript], (err) => {
      if (err) new Notice(T("Terminál se nepodařilo otevřít: {0}", err.message), 10000);
    });
    new Notice(T("Spouštím {0} v Terminálu: {1}", rezim === "claude" ? "Claude" : "AI", prikaz));
  }

  async vytvorUkol({ predmet, nazev, typ, termin, zdroj }) {
    const arg = [predmet, nazev];
    if (typ) arg.push("--typ", typ);
    if (termin) arg.push("--termin", termin);
    if (zdroj) arg.push("--z-dokumentu", zdroj);
    try {
      const [docx, poznamka] = (await this.spustPython("novy_ukol.py", arg)).split("\n");
      new Notice(T("Vytvořeno a otevírám ve Wordu:\n{0}", path.basename(docx)), 8000);
      if (poznamka) setTimeout(() => this.app.workspace.openLinkText(poznamka, "", true), 800);
    } catch (e) {
      this.chyba(T("Úkol se nepodařilo vytvořit: {0}", e.message), "novy-ukol");
    }
  }

  async oznacHotovo() {
    const f = this.app.workspace.getActiveFile();
    if (!f || this.app.metadataCache.getFileCache(f)?.frontmatter?.typ !== "ukol") {
      new Notice(T("Otevři nejdřív poznámku úkolu."));
      return;
    }
    await this.app.fileManager.processFrontMatter(f, (fm) => { fm.stav = "hotovo"; });
    await this.app.vault.process(f, (t) => t.replace(KROK_ODEVZDAT, "- [x] $1"));
    new Notice(T("✅ Úkol je odevzdaný – zmizí z termínů na Domově i v plánu."));
  }

  otevriRoadmap() {
    if (!this.app.commands.executeCommandById(this.data.roadmapPrikaz)) {
      new Notice(T("Plán Neuro Roadmap nejde otevřít – spouštím kontrolu."));
      this.kontrola({ automaticky: false });
    }
  }
};

class PotvrzeniModal extends Modal {
  constructor(plugin, zmenene) {
    super(plugin.app);
    this.plugin = plugin;
    this.zmenene = zmenene;
  }

  onOpen() {
    const { contentEl } = this;
    this.titleEl.setText(T("🛡 Potvrdit změny kódu?"));
    contentEl.createEl("p", { text: T("Tyto chráněné soubory se změnily od posledního potvrzení:") });
    const ul = contentEl.createEl("ul");
    for (const z of this.zmenene) ul.createEl("li", { text: z });
    contentEl.createEl("p", { text: T("Potvrď jen tehdy, když víš, že změny jsou tvoje (nebo je AI udělala na tvůj pokyn). Když nevíš, odkud jsou, zavři okno – skripty se do potvrzení nespustí."), cls: "setting-item-description" });
    const kod = String(Math.floor(1000 + Math.random() * 9000));
    let zadano = "";
    new Setting(contentEl).setName(T("Pro potvrzení opiš kód {0}", kod))
      .addText((t) => t.onChange((v) => (zadano = v.trim())));
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("Změny jsou moje – potvrdit")).setWarning().onClick(async () => {
        if (zadano !== kod) { new Notice(T("Kód nesouhlasí – nic nebylo potvrzeno.")); return; }
        this.close();
        await this.plugin.ulozIntegritu(this.zmenene);
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class UkolModal extends Modal {
  constructor(plugin, vychozi = {}) {
    super(plugin.app);
    this.plugin = plugin;
    this.data = { typ: "", termin: "", ...vychozi };
  }

  onOpen() {
    const { contentEl } = this;
    const predmety = this.plugin.predmety();
    if (!predmety.length) { contentEl.setText(T("Nenašel se žádný přehled předmětu (typ: predmet).")); return; }
    if (!this.data.predmet || !predmety.some((p) => p.nazev === this.data.predmet)) this.data.predmet = predmety[0].nazev;
    const n = this.plugin.nastaveni();
    const jazykWord = n.jazyk_word || n.jazyk || "cs";

    this.titleEl.setText(this.data.zdroj ? T("📄 Převést práci do šablony KISK") : T("📝 Nový úkol ve Wordu"));
    if (this.data.zdroj) contentEl.createEl("p", { text: T("Zdroj: {0} (originál zůstane beze změny)", this.data.zdroj), cls: "setting-item-description" });

    new Setting(contentEl).setName(T("Předmět")).addDropdown((d) => {
      for (const p of predmety) d.addOption(p.nazev, `${p.kod} ${p.nazev}`.trim());
      d.setValue(this.data.predmet).onChange((v) => (this.data.predmet = v));
    });
    new Setting(contentEl).setName(T("Název práce")).addText((t) => {
      t.setValue(this.data.nazev || "").onChange((v) => (this.data.nazev = v.trim()));
      setTimeout(() => t.inputEl.focus(), 50);
    });
    new Setting(contentEl).setName(T("Typ práce")).setDesc(T("Nepovinné – druhý řádek na titulní straně, např. Povinný domácí úkol č. 2"))
      .addText((t) => t.setValue(this.data.typ).onChange((v) => (this.data.typ = v.trim())));
    new Setting(contentEl).setName(T("Termín odevzdání")).setDesc(T("Nepovinné – ukáže se na Domově a v plánu Neuro Roadmap"))
      .addText((t) => { t.inputEl.type = "date"; t.setValue(this.data.termin).onChange((v) => (this.data.termin = v)); });
    contentEl.createEl("p", { cls: "setting-item-description",
      text: T("Dokument bude v jazyce: {0} (změníš v Nastavení → Second Brain for KISK → Jazyk dokumentů ve Wordu).", JAZYKY[jazykWord] || jazykWord) });
    new Setting(contentEl).addButton((b) => b.setButtonText(T("Vytvořit a otevřít ve Wordu")).setCta().onClick(() => {
      if (!this.data.nazev) { new Notice(T("Vyplň název práce.")); return; }
      this.close();
      this.plugin.vytvorUkol(this.data);
    }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class DocxVyber extends FuzzySuggestModal {
  constructor(plugin) {
    super(plugin.app);
    this.plugin = plugin;
    this.setPlaceholder(T("Vyber svou hotovou práci (.docx) z trezoru…"));
  }
  getItems() {
    return this.app.vault.getFiles().filter((f) => f.extension === "docx" && !f.path.startsWith("_Systém/"));
  }
  getItemText(f) {
    return f.path;
  }
  onChooseItem(f) {
    const predmet = f.path.split("/")[0];
    const prefix = this.plugin.vlastniPrefix();
    const nazev = (prefix && f.basename.startsWith(prefix) ? f.basename.slice(prefix.length).replace(/^\s*\S+\s+/, "") : f.basename)
      .replace(/[_-]+/g, " ").trim();
    new UkolModal(this.plugin, { predmet, nazev, zdroj: f.path }).open();
  }
}

class NastaveniTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    if (!this.koncept) this.koncept = { ai: "claude", ai_prikaz: "", jazyk: "cs", ...this.plugin.nastaveni() };
    const k = this.koncept;
    if (!k.jazyk_word) k.jazyk_word = k.jazyk || "cs";

    // Jazyk
    new Setting(containerEl).setName(T("🌐 Jazyk")).setHeading();
    new Setting(containerEl).setName(T("Jazyk rozhraní"))
      .setDesc(T("Tlačítka, nastavení, Domov, návod, šablony a poznámky od AI. Po uložení se systémové poznámky přeloží (předtím se udělá záloha); tvoje poznámky se nemění."))
      .addDropdown((d) => { for (const [kod, nazev] of Object.entries(JAZYKY)) d.addOption(kod, nazev);
        d.setValue(k.jazyk || "cs").onChange((v) => { k.jazyk = v; this.display(); }); });
    new Setting(containerEl).setName(T("Jazyk dokumentů ve Wordu"))
      .setDesc(T("Jazyk nadpisů a předvyplněných textů v nových úkolech ve Wordu. Může se lišit od jazyka rozhraní."))
      .addDropdown((d) => { for (const [kod, nazev] of Object.entries(JAZYKY)) d.addOption(kod, nazev);
        d.setValue(k.jazyk_word).onChange((v) => (k.jazyk_word = v)); });

    // AI
    new Setting(containerEl).setName(T("🤖 Práce s AI")).setHeading();
    containerEl.createEl("p", { cls: "setting-item-description", text:
      T("AI můžeš kdykoli přidat, změnit nebo odebrat. Bez AI zmizí tlačítka s AI a vše ostatní (Word, fronta, termíny, plán) funguje dál.") });
    new Setting(containerEl).setName(T("Režim AI")).addDropdown((d) => d
      .addOption("claude", T("Claude Code (doporučeno)"))
      .addOption("jina", T("Jiná AI v Terminálu (Gemini CLI, Codex…)"))
      .addOption("zadna", T("Bez AI – vše ručně"))
      .setValue(k.ai || "claude")
      .onChange((v) => { k.ai = v; this.display(); }));

    if (k.ai === "claude") {
      containerEl.createEl("p", { cls: "setting-item-description", text:
        T("Potřebuješ Claude Code (claude.com/claude-code) a předplatné Claude. Platí bezpečnostní pravidla z .claude/settings.json.") });
    } else if (k.ai === "jina") {
      new Setting(containerEl).setName(T("Předvolba")).setDesc(T("Vyplní příkaz za tebe.")).addDropdown((d) => d
        .addOption("", T("– vyber –")).addOption("gemini -i {prompt}", "Gemini CLI").addOption("codex {prompt}", "OpenAI Codex CLI")
        .onChange((v) => { if (v) { k.ai_prikaz = v; this.display(); } }));
      new Setting(containerEl).setName(T("Příkaz AI"))
        .setDesc(T("Musí obsahovat {prompt} (na jeho místo se vloží zadání). Povolené jsou jen písmena, čísla, mezery a . _ / = : -"))
        .addText((t) => t.setPlaceholder("gemini -i {prompt}").setValue(k.ai_prikaz || "").onChange((v) => (k.ai_prikaz = v.trim())));
      containerEl.createEl("p", { cls: "mod-warning druhy-mozek-varovani", text:
        T("⚠️ Bezpečnostní pravidla z .claude/settings.json platí jen pro Claude Code. U jiné AI nech zapnuté potvrzování příkazů a nikdy nepoužívej režim bez potvrzování (např. --yolo, --dangerously-…).") });
    } else {
      containerEl.createEl("p", { cls: "setting-item-description", text:
        T("Ruční režim: poznámky píšeš sám ze šablon (Cmd+P → Vložit šablonu), zpracované materiály odškrtneš tlačítkem ✔️ Označit materiál jako zpracovaný. Nic se nikam neposílá.") });
    }

    // Záloha (ukládá se hned)
    new Setting(containerEl).setName(T("💾 Automatická záloha")).setHeading();
    const z = this.plugin.data.zaloha;
    const ulozZalohu = async () => { await this.plugin.saveData(this.plugin.data); };
    containerEl.createEl("p", { cls: "setting-item-description", text:
      T("Zálohuje se sama 10 minut po změnách, hned po potvrzení kódu nebo nastavení a aspoň jednou denně.") + " " +
      (z.posledni ? T("Poslední záloha: {0}.", kdy(z.posledni)) : T("Zatím neproběhla.")) +
      (z.chyba ? " " + T("⚠️ Poslední pokus selhal: {0}", z.chyba) : "") });
    new Setting(containerEl).setName(T("Zálohovat automaticky"))
      .addToggle((t) => t.setValue(z.zapnuto).onChange(async (v) => { z.zapnuto = v; await ulozZalohu(); }));
    const mista = this.plugin.mistaZalohy();
    const vybrane = mista.find((m) => path.resolve(m.cesta) === path.resolve(z.slozka || "-"));
    if (this.vlastniCesta === undefined) this.vlastniCesta = vybrane ? "" : z.slozka;
    new Setting(containerEl).setName(T("Kam zálohovat"))
      .setDesc(T("OneDrive, Google Drive, Dropbox, iCloud, Dokumenty, externí disk nebo vlastní složka. Teď: {0}", z.slozka || T("nenastaveno")))
      .addDropdown((dd) => {
        mista.forEach((m, i) => dd.addOption(String(i), m.nazev));
        dd.addOption("vlastni", T("Vlastní složka…"));
        dd.setValue(vybrane ? String(mista.indexOf(vybrane)) : "vlastni");
        dd.onChange((v) => {
          if (v === "vlastni") { this.vlastniCesta = this.vlastniCesta || ""; this.display(); return; }
          this.vlastniCesta = "";
          new ZmenaZalohyModal(this.plugin, mista[Number(v)].cesta, () => this.display()).open();
        });
      });
    if (!vybrane || this.vlastniCesta) {
      new Setting(containerEl).setName(T("Vlastní složka")).setDesc(T("Celá cesta, např. /Volumes/Disk/Zálohy nebo ~/Desktop/Záloha."))
        .addText((t) => t.setValue(this.vlastniCesta || z.slozka || "").onChange((v) => (this.vlastniCesta = v.trim())))
        .addButton((b) => b.setButtonText(T("Použít")).onClick(() => {
          const cesta = (this.vlastniCesta || "").replace(/^~(?=\/|$)/, os.homedir());
          if (!path.isAbsolute(cesta)) { new Notice(T("Zadej celou cestu (začíná / nebo ~).")); return; }
          new ZmenaZalohyModal(this.plugin, path.join(cesta), () => this.display()).open();
        }));
    }
    new Setting(containerEl).setName(T("Počet uchovaných záloh"))
      .setDesc(T("Stará záloha se maže vždy až PO úspěšném vytvoření nové."))
      .addDropdown((dd) => { dd.addOption("1", T("1 – jen nejnovější")); for (const n of [3, 5, 10, 20, 30]) dd.addOption(String(n), String(n));
        dd.setValue(String(z.pocet)).onChange(async (v) => { z.pocet = Number(v); await ulozZalohu(); }); });
    new Setting(containerEl).setName(T("Zálohovat i studijní materiály"))
      .setDesc(T("PDF, prezentace, obrázky… Vypni, pokud je trezor už v cloudu (materiály tam jsou) – záloha bude malá."))
      .addToggle((t) => t.setValue(z.materialy).onChange(async (v) => { z.materialy = v; await ulozZalohu(); }));
    new Setting(containerEl).addButton((b) => b.setButtonText(T("💾 Zálohovat teď")).setCta()
      .onClick(async () => { await this.plugin.zalohuj({ tise: false }); this.display(); }));

    // Předměty (mění se hned)
    new Setting(containerEl).setName(T("📚 Předměty")).setHeading();
    containerEl.createEl("p", { cls: "setting-item-description", text:
      T("Podle předmětů se řídí Domov, termíny, výběr předmětu u úkolů ve Wordu, plán a levý panel.") });
    const predmety = this.plugin.predmety();
    if (!predmety.length) containerEl.createEl("p", { cls: "setting-item-description", text: T("Zatím žádné předměty.") });
    for (const pr of predmety) {
      new Setting(containerEl).setName(pr.kod ? `${pr.kod} · ${pr.nazev}` : pr.nazev)
        .addButton((b) => b.setButtonText(T("🗄 Archivovat")).setTooltip(T("Konec semestru – přesune předmět do _Archiv, nic se nemaže."))
          .onClick(async () => { if (await this.plugin.archivujPredmet(pr.soubor.parent?.path || pr.nazev)) setTimeout(() => this.display(), 800); }))
        .addButton((b) => b.setButtonText(T("🗑 Odebrat")).setWarning()
          .onClick(() => new PredmetOdebratModal(this.plugin, pr.soubor.parent?.path || pr.nazev, () => setTimeout(() => this.display(), 800)).open()));
    }
    new Setting(containerEl).addButton((b) => b.setButtonText(T("📚 Přidat předmět")).setCta()
      .onClick(() => new PredmetNovyModal(this.plugin, () => setTimeout(() => this.display(), 1500)).open()));
    const archiv = this.plugin.archivovane();
    if (archiv.length) {
      containerEl.createEl("p", { cls: "setting-item-description", text: T("🗄 V archivu (_Archiv):") });
      for (const nazev of archiv) {
        new Setting(containerEl).setName(nazev).addButton((b) => b.setButtonText(T("↩️ Vrátit z archivu"))
          .onClick(async () => { if (await this.plugin.vratZArchivu(nazev)) setTimeout(() => this.display(), 800); }));
      }
    }

    // Připomínky (ukládá se hned)
    new Setting(containerEl).setName(T("⏰ Připomínky termínů")).setHeading();
    new Setting(containerEl).setName(T("Připomínat termíny"))
      .setDesc(T("Jednou denně při spuštění Obsidianu upozorní na úkoly a zkoušky do 3 dnů a na ty po termínu."))
      .addToggle((t) => t.setValue(this.plugin.data.pripominky.zapnuto)
        .onChange(async (v) => { this.plugin.data.pripominky.zapnuto = v; await this.plugin.saveData(this.plugin.data); }))
      .addButton((b) => b.setButtonText(T("⏰ Ukázat teď")).onClick(() => this.plugin.pripomenTerminy({ vzdy: true })));

    // Hlášení chyb
    new Setting(containerEl).setName(T("🐞 Chyba nebo nápad?")).setHeading();
    new Setting(containerEl).setName(T("Nahlásit chybu nebo nápad"))
      .setDesc(T("Otevře okno, kde napíšeš, co se stalo. Technické údaje jsou bez osobních dat a uvidíš je předem; nic se neodešle samo."))
      .addButton((b) => b.setButtonText(T("🐞 Nahlásit")).onClick(() => new HlaseniModal(this.plugin).open()));

    // Aktualizace (ukládá se hned)
    new Setting(containerEl).setName(T("🔄 Aktualizace")).setHeading();
    const a = this.plugin.data.aktualizace;
    if (DISTRIBUCE === "obsidian") {
      containerEl.createEl("p", { cls: "setting-item-description", text:
        T("Nainstalovaná verze: {0}.", this.plugin.verze()) + " " +
        T("Druhý mozek z adresáře Obsidianu aktualizuje Obsidian: Nastavení → Pluginy třetích stran → Zkontrolovat aktualizace.") });
      new Setting(containerEl).setName(T("Obnovit soubory v trezoru"))
        .setDesc(T("Po aktualizaci rozšíření srovná skripty, šablony a systémové poznámky s novou verzí. Upravené poznámky zůstanou."))
        .addButton((b) => b.setButtonText(T("🔄 Obnovit")).onClick(async () => {
          try { await this.plugin.obnovSoubory(); } catch (e) { this.plugin.chyba(T("Nepodařilo se: {0}", e.message), "obnova"); }
          this.display();
        }));
    }
    const novejsi = DISTRIBUCE === "github" && a.nejnovejsi && novejsiVerze(a.nejnovejsi.verze, this.plugin.verze());
    containerEl.createEl("p", { cls: "setting-item-description", text:
      T("Nainstalovaná verze: {0}.", this.plugin.verze()) + " " +
      (a.nejnovejsi ? T("Nejnovější na GitHubu: {0}.", a.nejnovejsi.verze) : "") + " " +
      (a.posledni ? T("Zkontrolováno: {0}.", kdy(a.posledni)) : "") +
      (a.chyba ? " " + T("⚠️ Poslední pokus selhal: {0}", a.chyba) : "") });
    if (DISTRIBUCE === "github") new Setting(containerEl).setName(T("Hlídat nové verze"))
      .setDesc(T("Jednou denně se zeptá GitHubu na číslo poslední verze – nic se neodesílá a nic se neinstaluje samo. Když vyjde nová, nabídne seznam změn a stažení."))
      .addToggle((t) => t.setValue(a.kontrolovat).onChange(async (v) => { a.kontrolovat = v; await this.plugin.saveData(this.plugin.data); }));
    if (DISTRIBUCE === "github") new Setting(containerEl)
      .addButton((b) => b.setButtonText(T("🔄 Zkontrolovat teď"))
        .onClick(async () => { await this.plugin.zkontrolujAktualizace({ automaticky: false }); this.display(); }))
      .then((st) => { if (novejsi) st.addButton((b) => b.setButtonText(T("⬇️ Aktualizovat na {0}", a.nejnovejsi.verze)).setCta()
        .onClick(() => new AktualizaceModal(this.plugin, a.nejnovejsi).open())); });
    const posledni = this.plugin.posledniAktualizace();
    if (posledni) {
      new Setting(containerEl).setName(T("↩️ Vrátit poslední aktualizaci"))
        .setDesc(T("Pro případ nouze: vrátí soubory, které změnila aktualizace {0} → {1}. Jde to {2} dní po aktualizaci.", posledni.z, posledni.na, ZALOHA_AKTUALIZACE_DNI))
        .addButton((b) => b.setButtonText(T("↩️ Vrátit")).setWarning().onClick(() => new VratitModal(this.plugin, posledni, () => this.display()).open()));
    }

    // Osobní údaje
    new Setting(containerEl).setName(T("👤 Osobní údaje (záhlaví prací ve Wordu)")).setHeading();
    new Setting(containerEl).setName(T("Jméno a příjmení")).addText((t) => t.setValue(k.jmeno || "").onChange((v) => (k.jmeno = v.trim())));
    new Setting(containerEl).setName(T("Jméno v názvu souborů")).setDesc(T("Jak odevzdáváš do ISu, obvykle Příjmení Jméno."))
      .addText((t) => t.setValue(k.jmeno_soubor || "").onChange((v) => (k.jmeno_soubor = v.trim())));
    new Setting(containerEl).setName("UČO").addText((t) => t.setValue(k.uco || "").onChange((v) => (k.uco = v.trim())));

    new Setting(containerEl)
      .setDesc(T("Jazyk, AI a osobní údaje se uloží tlačítkem Uložit."))
      .addButton((b) => b.setButtonText(T("Zahodit změny")).onClick(() => { this.koncept = null; this.display(); }))
      .addButton((b) => b.setButtonText(T("Uložit")).setCta().onClick(async () => {
        if (!/^[0-9]{4,7}$/.test(k.uco || "")) { new Notice(T("UČO má být číslo (4–7 číslic).")); return; }
        if (!k.jmeno || !k.jmeno_soubor) { new Notice(T("Vyplň jméno i jméno v názvu souborů.")); return; }
        if (k.ai === "jina" && !BEZPECNY_AI_PRIKAZ.test(k.ai_prikaz || "")) { new Notice(T("Příkaz AI je neplatný – viz popis u pole.")); return; }
        const puvodni = this.plugin.nastaveni();
        const nove = { jmeno: k.jmeno, jmeno_soubor: k.jmeno_soubor, uco: k.uco, ai: k.ai, ai_prikaz: k.ai === "jina" ? k.ai_prikaz : "",
          jazyk: k.jazyk || "cs", jazyk_word: k.jazyk_word || k.jazyk || "cs" };
        const uloz = async () => { await this.plugin.ulozNastaveni(nove, puvodni); this.koncept = null; this.display(); };
        if ((puvodni.jazyk || "cs") !== nove.jazyk) new JazykModal(this.plugin, nove.jazyk, uloz).open();
        else await uloz();
      }));
  }

  hide() {
    this.koncept = null;
    this.vlastniCesta = undefined;
  }
}

class PredmetNovyModal extends Modal {
  constructor(plugin, hotovo) {
    super(plugin.app);
    this.plugin = plugin;
    this.hotovo = hotovo;
    this.kod = "";
    this.nazev = "";
  }

  onOpen() {
    const { contentEl } = this;
    this.titleEl.setText(T("📚 Přidat předmět"));
    new Setting(contentEl).setName(T("Kód předmětu")).setDesc(T("Jak je v ISu, např. ISKB02. Může zůstat prázdný."))
      .addText((t) => t.setPlaceholder("ISKB02").onChange((v) => (this.kod = v.trim())));
    new Setting(contentEl).setName(T("Název předmětu")).setDesc(T("Podle něj se pojmenuje složka i přehled předmětu."))
      .addText((t) => t.setPlaceholder(T("Úvod do knihovnictví")).onChange((v) => (this.nazev = v.trim())));
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("Přidat")).setCta().onClick(async () => {
        if (!this.nazev) { new Notice(T("Vyplň název předmětu.")); return; }
        if (this.kod && !/^(?=.*\d)[A-Za-z0-9][A-Za-z0-9_.-]{1,14}$/.test(this.kod)) {
          new Notice(T("Kód má být jako v ISu – písmena a číslice, např. ISKB02.")); return;
        }
        try {
          await this.plugin.pridejPredmet(this.kod, this.nazev);
          this.close();
          this.hotovo?.();
        } catch (e) {
          this.plugin.chyba(T("Předmět se nepodařilo přidat: {0}", e.message), "predmet");
        }
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class PredmetOdebratModal extends Modal {
  constructor(plugin, nazev, hotovo) {
    super(plugin.app);
    this.plugin = plugin;
    this.nazev = nazev;
    this.hotovo = hotovo;
  }

  onOpen() {
    const { contentEl } = this;
    this.titleEl.setText(T("🗑 Odebrat předmět {0}?", this.nazev));
    contentEl.createEl("p", { text: T("Celá složka předmětu – materiály, poznámky i úkoly – se přesune do koše v macOS. Dokud koš nevysypeš, můžeš ji odtamtud vrátit.") });
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("🗑 Přesunout do koše")).setWarning().onClick(async () => {
        this.close();
        await this.plugin.odeberPredmet(this.nazev);
        this.hotovo?.();
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class AktualizaceModal extends Modal {
  constructor(plugin, nova) {
    super(plugin.app);
    this.plugin = plugin;
    this.nova = nova;
  }

  onOpen() {
    const { contentEl } = this;
    const { verze, stranka, zip } = this.nova;
    this.titleEl.setText(T("🆕 Je dostupná nová verze druhého mozku"));
    contentEl.createEl("p", { text: T("Verze {0} (máš {1}).", verze, this.plugin.verze()) });
    contentEl.createEl("p", { cls: "setting-item-description", text:
      T("Stáhne se z GitHubu a ověří. Pak už jen klikneš na Instalovat (nebo Zrušit instalaci). Tvoje poznámky, materiály, předměty a nastavení zůstanou; před instalací se udělá záloha a aktualizaci jde vrátit.") });
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("📋 Co je nového")).onClick(() => window.open(stranka)))
      .addButton((b) => b.setButtonText(T("Teď ne")).onClick(() => { this.plugin.odlozenaVerze = verze; this.close(); }))
      .addButton((b) => b.setButtonText(T("⬇️ Stáhnout a nainstalovat")).setCta().onClick(() => {
        this.plugin.odlozenaVerze = verze;
        this.close();
        new InstalaceModal(this.plugin, this.nova).open();
      }));
    const rucne = contentEl.createEl("p", { cls: "setting-item-description" });
    rucne.createEl("a", { text: T("Nebo stáhnout ručně a nainstalovat přes Instalovat.command"), href: zip });
  }

  onClose() {
    this.contentEl.empty();
  }
}

class PruvodceModal extends Modal {
  constructor(plugin) {
    super(plugin.app);
    this.plugin = plugin;
    this.v = { jazyk: "cs", jazykWord: "cs", jmeno: "", jmenoSoubor: "", uco: "", predmety: [], ai: "zadna", aiPrikaz: "" };
    this.python = null;
  }

  async onOpen() {
    this.vykresli();
    this.python = await this.plugin.pythonFunguje();
    this.vykresli();
  }

  vykresli() {
    const { contentEl } = this;
    const v = this.v;
    contentEl.empty();
    this.titleEl.setText(T("🧠 Nastavit druhý mozek v tomto trezoru"));
    contentEl.createEl("p", { cls: "setting-item-description", text:
      T("Založí Domov, návod, šablony, předměty a skripty. Nic, co už v trezoru máš, se nepřepíše. Všechno změníš později v Nastavení → Second Brain for KISK.") });
    new Setting(contentEl).setName(T("Jazyk")).addDropdown((d) => { for (const [k, n] of Object.entries(JAZYKY)) d.addOption(k, n);
      d.setValue(v.jazyk).onChange((x) => { v.jazyk = x; v.jazykWord = x; this.plugin.nastavJazykRozhrani(x); this.vykresli(); }); });
    new Setting(contentEl).setName(T("Jazyk dokumentů ve Wordu")).addDropdown((d) => { for (const [k, n] of Object.entries(JAZYKY)) d.addOption(k, n);
      d.setValue(v.jazykWord).onChange((x) => (v.jazykWord = x)); });
    new Setting(contentEl).setName(T("Jméno a příjmení")).addText((t) => t.setValue(v.jmeno).onChange((x) => {
      v.jmeno = x.trim();
      const casti = v.jmeno.split(/\s+/);
      if (!this.jmenoRucne) v.jmenoSoubor = casti.length > 1 ? [casti.at(-1), ...casti.slice(0, -1)].join(" ") : v.jmeno;
    }));
    new Setting(contentEl).setName(T("Jméno v názvu souborů")).setDesc(T("Jak odevzdáváš do ISu, obvykle Příjmení Jméno. Prázdné = podle jména."))
      .addText((t) => t.setValue("").onChange((x) => { this.jmenoRucne = !!x.trim(); if (x.trim()) v.jmenoSoubor = x.trim(); }));
    new Setting(contentEl).setName("UČO").addText((t) => t.setValue(v.uco).onChange((x) => (v.uco = x.trim())));
    contentEl.createEl("div", { text: T("Tvoje předměty – každý na samostatný řádek ve tvaru KÓD Název (např. ISKB02 Úvod do knihovnictví). Prázdné = ukázkový předmět."), cls: "setting-item-name" });
    const ta = contentEl.createEl("textarea", { cls: "druhy-mozek-hlaseni" });
    ta.rows = 5;
    ta.value = v.predmety.join("\n");
    ta.addEventListener("input", () => (v.predmety = ta.value.split("\n").map((x) => x.trim()).filter(Boolean)));
    new Setting(contentEl).setName(T("Režim AI")).addDropdown((d) => d
      .addOption("zadna", T("Bez AI – vše ručně")).addOption("claude", T("Claude Code (doporučeno)")).addOption("jina", T("Jiná AI v Terminálu (Gemini CLI, Codex…)"))
      .setValue(v.ai).onChange((x) => { v.ai = x; this.vykresli(); }));
    if (v.ai === "jina") new Setting(contentEl).setName(T("Příkaz AI"))
      .setDesc(T("Musí obsahovat {prompt} (na jeho místo se vloží zadání). Povolené jsou jen písmena, čísla, mezery a . _ / = : -"))
      .addText((t) => t.setPlaceholder("gemini -i {prompt}").setValue(v.aiPrikaz).onChange((x) => (v.aiPrikaz = x.trim())));
    const py = contentEl.createEl("p", { cls: "setting-item-description" });
    if (this.python === null) py.setText(T("⏳ Kontroluji Python 3…"));
    else if (this.python) py.setText(T("✅ Python 3 je nainstalovaný."));
    else {
      py.setText(T("❌ Chybí Python 3 – druhý mozek ho potřebuje (fronta, Word, přehledy). Nainstaluj ho z python.org a klikni Zkontrolovat znovu."));
      new Setting(contentEl)
        .addButton((b) => b.setButtonText(T("Otevřít python.org")).onClick(() => window.open("https://www.python.org/downloads/")))
        .addButton((b) => b.setButtonText(T("Zkontrolovat znovu")).onClick(async () => { this.python = await this.plugin.pythonFunguje(); this.vykresli(); }));
    }
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Teď ne")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("🧠 Nastavit")).setCta().setDisabled(!this.python).onClick(async () => {
        if (!v.jmeno) { new Notice(T("Vyplň jméno i jméno v názvu souborů.")); return; }
        if (!/^[0-9]{4,7}$/.test(v.uco)) { new Notice(T("UČO má být číslo (4–7 číslic).")); return; }
        if (v.ai === "jina" && !BEZPECNY_AI_PRIKAZ.test(v.aiPrikaz)) { new Notice(T("Příkaz AI je neplatný – viz popis u pole.")); return; }
        v.jmenoSoubor = v.jmenoSoubor || v.jmeno;
        this.close();
        await this.plugin.nastavTrezor(v);
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class ObnovaSouboruModal extends Modal {
  constructor(plugin, puvodni) {
    super(plugin.app);
    this.plugin = plugin;
    this.puvodni = puvodni;
  }

  onOpen() {
    const { contentEl } = this;
    this.titleEl.setText(T("🔄 Druhý mozek byl aktualizován na verzi {0}", BALIK.verze));
    contentEl.createEl("p", { text: T("Obnovit i soubory v trezoru (skripty, šablony, systémové poznámky)? Předtím se zazálohují; upravené poznámky zůstanou a nová verze se uloží vedle. Tvoje poznámky, materiály a nastavení se nemění.") });
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Teď ne")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("🔄 Obnovit")).setCta().onClick(async () => {
        this.close();
        try { await this.plugin.obnovSoubory(); } catch (e) { this.plugin.chyba(T("Nepodařilo se: {0}", e.message), "obnova"); }
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class HlaseniModal extends Modal {
  constructor(plugin, chyba = "") {
    super(plugin.app);
    this.plugin = plugin;
    this.co = chyba ? plugin.anonymizuj(chyba) : "";
    this.pred = "";
    this.priloha = true;
    this.udaje = plugin.diagnostika();
  }

  text() {
    return [
      `## ${T("Co se stalo")}`, this.co || "–", "",
      `## ${T("Co jsem dělal(a) předtím")}`, this.pred || "–", "",
      ...(this.priloha ? [`## ${T("Technické údaje (bez osobních dat)")}`, "```", this.udaje, "```"] : []),
    ].join("\n");
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    this.titleEl.setText(T("🐞 Nahlásit chybu nebo nápad"));
    contentEl.createEl("p", { cls: "setting-item-description", text:
      T("Nic se neodešle samo. Vidíš všechno, co se pošle, a můžeš to upravit. Neposílej hesla ani obsah svých poznámek.") });
    const pole = (nazev, hodnota, nastav, radku = 4) => {
      contentEl.createEl("div", { text: nazev, cls: "setting-item-name" });
      const ta = contentEl.createEl("textarea", { cls: "druhy-mozek-hlaseni" });
      ta.rows = radku;
      ta.value = hodnota;
      ta.addEventListener("input", () => nastav(ta.value));
    };
    pole(T("Co se stalo? (nebo co by se hodilo)"), this.co, (v) => (this.co = v));
    pole(T("Co jsi dělal(a) předtím?"), this.pred, (v) => (this.pred = v), 3);
    new Setting(contentEl).setName(T("Přiložit technické údaje")).setDesc(T("Verze, jazyk, režim AI, výsledek kontroly a poslední chyby – bez jména, UČO, cest a obsahu poznámek."))
      .addToggle((t) => t.setValue(this.priloha).onChange((v) => (this.priloha = v)));
    pole(T("Technické údaje (můžeš upravit)"), this.udaje, (v) => (this.udaje = v), 8);
    contentEl.createEl("p", { cls: "setting-item-description", text:
      T("📧 E-mail odejde z adresy nastavené v aplikaci Mail a příjemce ji uvidí. Nechceš ji prozradit? Nahlas to na GitHubu – tam je vidět jen tvoje uživatelské jméno.") });
    const predmet = `[Druhý mozek ${this.plugin.verze()}] ` + (this.co.split("\n")[0].slice(0, 60) || T("Hlášení"));
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("🐙 Nahlásit na GitHubu")).onClick(() => {
        window.open(`https://github.com/${REPOZITAR}/issues/new?labels=bug&title=${encodeURIComponent(predmet)}&body=${encodeURIComponent(this.text().slice(0, 6000))}`);
        this.close();
      }))
      .addButton((b) => b.setButtonText(T("📧 Odeslat e-mailem")).setCta().onClick(() => {
        window.open(`mailto:${HLASENI_EMAIL}?subject=${encodeURIComponent(predmet)}&body=${encodeURIComponent(this.text().slice(0, 1800))}`);
        new Notice(T("📧 Otevřel se e-mail s hlášením – zkontroluj ho a odešli. Díky!"), 8000);
        this.close();
      }));
    const bezpecnost = contentEl.createEl("p", { cls: "setting-item-description" });
    bezpecnost.appendText(T("Bezpečnostní problém? Nahlas ho soukromě: "));
    bezpecnost.createEl("a", { text: T("soukromé hlášení na GitHubu"), href: `https://github.com/${REPOZITAR}/security/advisories/new` });
    bezpecnost.appendText(T(" nebo e-mailem s předmětem [SECURITY]."));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class KartickyModal extends Modal {
  constructor(plugin) {
    super(plugin.app);
    this.plugin = plugin;
    this.predmet = "";
    this.stav = "vyber";
  }

  async onOpen() {
    this.vsechny = await this.plugin.nactiKarticky("");
    this.vykresli();
  }

  k_opakovani(predmet) {
    return this.vsechny.filter((k) => (!predmet || k.soubor.startsWith(predmet + "/")) && this.plugin.kartickaKOpakovani(k));
  }

  zacni() {
    const karty = this.k_opakovani(this.predmet);
    for (let i = karty.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [karty[i], karty[j]] = [karty[j], karty[i]]; }
    this.fronta = karty.slice(0, KARTICKY_ZA_SEZENI);
    this.celkem = this.fronta.length;
    this.vim = 0;
    this.nevim = 0;
    this.stav = this.fronta.length ? "otazka" : "konec";
    this.vykresli();
  }

  vykresli() {
    const { contentEl } = this;
    contentEl.empty();
    this.titleEl.setText(T("🃏 Opakovat kartičky"));
    if (this.stav === "vyber") {
      if (!this.vsechny.length) {
        contentEl.createEl("p", { text: T("Zatím nemáš žádné kartičky. Piš je do poznámek jako řádek Otázka::Odpověď.") });
        return;
      }
      new Setting(contentEl).setName(T("Předmět")).addDropdown((d) => {
        d.addOption("", T("Všechny předměty") + ` (${this.k_opakovani("").length})`);
        for (const p of this.plugin.predmety()) d.addOption(p.nazev, `${p.kod} ${p.nazev} (${this.k_opakovani(p.nazev).length})`.trim());
        d.setValue(this.predmet).onChange((v) => { this.predmet = v; this.vykresli(); });
      });
      contentEl.createEl("p", { cls: "setting-item-description", text:
        T("K opakování dnes: {0} z {1} kartiček. Co umíš, se vrátí za 1, 2, 4, 8… dní; co ne, hned zítra.", this.k_opakovani(this.predmet).length, this.vsechny.length) });
      new Setting(contentEl).addButton((b) => b.setButtonText(T("▶️ Začít")).setCta().onClick(() => this.zacni()));
      return;
    }
    if (this.stav === "konec") {
      contentEl.createEl("p", { text: this.celkem ? T("Hotovo! ✅ Vím: {0} · ❌ Nevím: {1}", this.vim, this.nevim) : T("Dnes nic k opakování – skvělé! 🎉") });
      new Setting(contentEl).addButton((b) => b.setButtonText(T("Zavřít")).setCta().onClick(() => this.close()));
      return;
    }
    const k = this.fronta[0];
    contentEl.createEl("p", { cls: "setting-item-description", text: `${this.celkem - this.fronta.length + 1} / ${this.celkem} · ${k.soubor.split("/").pop().replace(/\.md$/, "")}` });
    contentEl.createEl("h4", { text: k.otazka });
    if (this.stav === "otazka") {
      new Setting(contentEl).addButton((b) => b.setButtonText(T("👀 Ukázat odpověď")).setCta().onClick(() => { this.stav = "odpoved"; this.vykresli(); }));
      return;
    }
    contentEl.createEl("p", { text: k.odpoved });
    const dalsi = async (vim) => {
      await this.plugin.ohodnotKarticku(k, vim);
      this.fronta.shift();
      if (vim) this.vim++; else { this.nevim++; if (!k.znovu) { k.znovu = true; this.fronta.push(k); } }  // co nevím, přijde v sezení ještě jednou
      this.stav = this.fronta.length ? "otazka" : "konec";
      this.vykresli();
    };
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("❌ Nevím")).onClick(() => dalsi(false)))
      .addButton((b) => b.setButtonText(T("✅ Vím")).setCta().onClick(() => dalsi(true)));
  }

  onClose() {
    this.contentEl.empty();
  }
}

const CITACE_POLE = {
  kniha: ["autori", "nazev", "podnazev", "vydani", "misto", "nakladatel", "rok", "isbn", "url"],
  clanek: ["autori", "nazev", "casopis", "rok", "rocnik", "cislo", "strany", "issn", "doi", "url"],
  web: ["autori", "nazev", "nakladatel", "rok", "url", "cit_datum"],
  kapitola: ["autori", "nazev", "editori", "kniha", "misto", "nakladatel", "rok", "strany", "isbn"],
};

class CitaceModal extends Modal {
  constructor(plugin) {
    super(plugin.app);
    this.plugin = plugin;
    this.data = { typ: "kniha" };
  }

  onOpen() {
    this.vykresli();
  }

  vykresli() {
    const { contentEl } = this;
    contentEl.empty();
    this.titleEl.setText(T("📚 Citace zdroje (ČSN ISO 690)"));
    const popisky = {
      autori: [T("Autoři"), T("Příjmení, Jméno; další autor… – nebo název organizace")], nazev: [T("Název")], podnazev: [T("Podnázev")],
      vydani: [T("Vydání"), T("Číslo vydání, např. 2 (první vydání se neuvádí)")], misto: [T("Místo vydání")], nakladatel: [T("Nakladatel / vydavatel")],
      rok: [T("Rok")], isbn: ["ISBN"], issn: ["ISSN"], doi: ["DOI"], url: ["URL"], casopis: [T("Časopis")], rocnik: [T("Ročník")],
      cislo: [T("Číslo")], strany: [T("Strany"), T("např. 12–15")], editori: [T("Editoři"), T("Příjmení, Jméno; …")], kniha: [T("Název knihy")],
      cit_datum: [T("Datum citování"), T("RRRR-MM-DD, prázdné = dnes")],
    };
    new Setting(contentEl).setName(T("Druh zdroje")).addDropdown((d) => d
      .addOption("kniha", T("Kniha")).addOption("clanek", T("Článek v časopise")).addOption("web", T("Webová stránka"))
      .addOption("kapitola", T("Kapitola v knize")).setValue(this.data.typ)
      .onChange((v) => { this.data.typ = v; this.vykresli(); }));
    for (const pole of CITACE_POLE[this.data.typ]) {
      const [nazev, popis] = popisky[pole];
      const s = new Setting(contentEl).setName(nazev).addText((t) => t.setValue(this.data[pole] || "").onChange((v) => (this.data[pole] = v)));
      if (popis) s.setDesc(popis);
    }
    contentEl.createEl("p", { cls: "setting-item-description", text: T("Citace se zkopíruje do schránky a uloží se do poznámky v _Zdroje. Zkontroluj ji podle požadavků vyučujícího.") });
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("📚 Vytvořit citaci")).setCta().onClick(async () => {
        if (!String(this.data.nazev || "").trim()) { new Notice(T("Vyplň aspoň název.")); return; }
        const data = Object.fromEntries(Object.entries(this.data).filter(([k]) => k === "typ" || CITACE_POLE[this.data.typ].includes(k)));
        try {
          const vystup = await this.plugin.spustPython("prehledy.py", ["--citace", JSON.stringify(data)]);
          const radky = vystup.split("\n").filter(Boolean);
          const citace = radky[0].replace(/^[^:]*:\s*/, "");
          try { await navigator.clipboard.writeText(citace.replace(/\*/g, "")); } catch (e) { /* schránka nemusí být dostupná */ }
          new Notice(T("📋 Citace je ve schránce: {0}", citace.replace(/\*/g, "")), 12000);
          this.close();
          await this.app.workspace.openLinkText(radky.pop(), "", true);
        } catch (e) {
          this.plugin.chyba(T("Nepodařilo se: {0}", e.message), "citace");
        }
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class InstalaceModal extends Modal {
  constructor(plugin, nova) {
    super(plugin.app);
    this.plugin = plugin;
    this.nova = nova;
    this.stav = "stahuji";
  }

  onOpen() {
    this.vykresli();
    this.plugin.pripravAktualizaci(this.nova, (stav) => { this.stav = stav; this.vykresli(); }, () => this.zruseno)
      .then((balik) => { if (this.zruseno) { this.plugin.uklidBalik(balik); return; } this.balik = balik; })
      .catch((e) => { this.stav = "chyba"; this.chyba = e.message; this.vykresli(); });
  }

  vykresli() {
    const { contentEl } = this;
    contentEl.empty();
    this.titleEl.setText(T("🔄 Aktualizace na verzi {0}", this.nova.verze));
    const poradi = ["stahuji", "overuji", "pripraveno"];
    const kroky = contentEl.createEl("ul", { cls: "druhy-mozek-kroky" });
    const ikona = (k) => this.stav === "chyba" ? (poradi.indexOf(k) < poradi.indexOf(this.posledni || "stahuji") ? "✅" : "⏸")
      : poradi.indexOf(k) < poradi.indexOf(this.stav) || this.stav === "instaluji" || this.stav === "hotovo" ? "✅"
      : k === this.stav ? "⏳" : "▫️";
    if (this.stav !== "chyba") this.posledni = this.stav;
    kroky.createEl("li", { text: `${ikona("stahuji")} ` + T("Stažení z GitHubu") });
    kroky.createEl("li", { text: `${ikona("overuji")} ` + T("Ověření kontrolních součtů a verze") });
    kroky.createEl("li", { text: `${this.stav === "hotovo" ? "✅" : this.stav === "instaluji" ? "⏳" : "▫️"} ` + T("Záloha a instalace") });

    if (this.stav === "chyba") {
      contentEl.createEl("p", { cls: "mod-warning", text: "❌ " + this.chyba });
      contentEl.createEl("p", { cls: "setting-item-description", text: T("V trezoru se nic nezměnilo.") });
      new Setting(contentEl)
        .addButton((b) => b.setButtonText(T("🐞 Nahlásit")).onClick(() => { this.close(); new HlaseniModal(this.plugin, this.chyba).open(); }))
        .addButton((b) => b.setButtonText(T("Zavřít")).onClick(() => this.close()));
      return;
    }
    if (this.stav === "pripraveno") {
      contentEl.createEl("p", { text: T("✅ Ověřeno – připraveno k instalaci. Před instalací se udělá záloha; poznámky, materiály, předměty a nastavení zůstanou.") });
    } else if (this.stav === "instaluji") {
      contentEl.createEl("p", { text: T("⏳ Instaluji… nezavírej Obsidian.") });
      return;
    } else if (this.stav === "hotovo") {
      contentEl.createEl("p", { text: T("✅ Hotovo. Rozšíření se znovu načte.") });
      new Setting(contentEl).addButton((b) => b.setButtonText(T("Zavřít")).setCta().onClick(() => this.close()));
      return;
    } else {
      contentEl.createEl("p", { cls: "setting-item-description", text: T("V trezoru se zatím nic nemění – zrušit můžeš kdykoli.") });
    }
    const s = new Setting(contentEl).addButton((b) => b.setButtonText(T("Zrušit instalaci")).onClick(() => this.close()));
    if (this.stav === "pripraveno") s.addButton((b) => b.setButtonText(T("✅ Instalovat")).setCta().onClick(async () => {
      this.stav = "instaluji"; this.vykresli();
      try {
        await this.plugin.instalujAktualizaci(this.balik);
        this.balik = null;
        this.stav = "hotovo";
      } catch (e) {
        this.balik = null;
        this.stav = "chyba";
        this.chyba = T("Instalace se nepovedla a změny se vrátily: {0}", e.message);
      }
      this.vykresli();
    }));
  }

  onClose() {
    if (this.stav !== "instaluji") {
      this.zruseno = true;
      this.plugin.uklidBalik(this.balik);
      this.balik = null;
    }
    this.contentEl.empty();
  }
}

class VratitModal extends Modal {
  constructor(plugin, aktualizace, hotovo) {
    super(plugin.app);
    this.plugin = plugin;
    this.aktualizace = aktualizace;
    this.hotovo = hotovo;
  }

  onOpen() {
    const { contentEl } = this;
    const { z, na, nahrazeno = [], nove = [] } = this.aktualizace;
    this.titleEl.setText(T("↩️ Vrátit aktualizaci {0} → {1}?", z, na));
    contentEl.createEl("p", { text: T("Vrátí se {0} souborů systému do stavu před aktualizací; {1} nových souborů se přesune do zálohy. Poznámky, materiály, předměty a nastavení se nemění.", nahrazeno.length, nove.length) });
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("↩️ Vrátit")).setWarning().onClick(async () => {
        this.close();
        try { await this.plugin.vratAktualizaci(); } catch (e) { this.plugin.chyba(T("Vrácení se nepovedlo: {0}", e.message), "vraceni"); }
        this.hotovo?.();
      }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class JazykModal extends Modal {
  constructor(plugin, jazyk, potvrzeno) {
    super(plugin.app);
    this.plugin = plugin;
    this.jazyk = jazyk;
    this.potvrzeno = potvrzeno;
  }

  onOpen() {
    const { contentEl } = this;
    this.titleEl.setText(`🌐 ${JAZYKY[this.jazyk]}`);
    contentEl.createEl("p", { text: T("Přepnout jazyk rozhraní na {0}?", JAZYKY[this.jazyk]) });
    contentEl.createEl("p", { cls: "setting-item-description", text:
      T("Přeloží se tlačítka, nastavení a systémové poznámky: Domov, Návod, šablony, rozcestníky a tabulky. Tyto poznámky se přepíšou – pokud jsi do nich psal, najdeš původní verzi v záloze, která se udělá předem. Tvoje vlastní poznámky, úkoly a materiály se nezmění.") });
    new Setting(contentEl)
      .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => this.close()))
      .addButton((b) => b.setButtonText(T("Přepnout jazyk")).setCta().onClick(async () => { this.close(); await this.potvrzeno(); }));
  }

  onClose() {
    this.contentEl.empty();
  }
}

class ZmenaZalohyModal extends Modal {
  constructor(plugin, nova, poZmene) {
    super(plugin.app);
    this.plugin = plugin;
    this.nova = nova;
    this.poZmene = poZmene;
  }

  onOpen() {
    const { contentEl } = this;
    const stara = this.plugin.data.zaloha.slozka;
    const pocet = stara ? this.plugin.pocetZaloh(stara) : 0;
    this.titleEl.setText(T("💾 Změnit místo zálohy"));
    contentEl.createEl("p", { text: T("Nové zálohy se budou ukládat do:") });
    contentEl.createEl("p", { text: this.nova, cls: "setting-item-description" });
    const hotovo = async (smazat) => { this.close(); await this.plugin.zmenSlozkuZalohy(this.nova, smazat); this.poZmene(); };
    if (pocet > 0) {
      contentEl.createEl("p", { text: T("Ve staré složce je {0} záloh: {1}", pocet, stara) });
      contentEl.createEl("p", { cls: "setting-item-description", text:
        T("Nejdřív se vytvoří záloha v nové složce. Staré zálohy se smažou, jen když se nová povede – a jen složky záloh (s datem), nic jiného.") });
      new Setting(contentEl)
        .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => { this.close(); this.poZmene(); }))
        .addButton((b) => b.setButtonText(T("Ponechat staré zálohy")).onClick(() => hotovo(false)))
        .addButton((b) => b.setButtonText(T("Smazat staré po úspěšné záloze do nové")).setWarning().onClick(() => hotovo(true)));
    } else {
      new Setting(contentEl)
        .addButton((b) => b.setButtonText(T("Zrušit")).onClick(() => { this.close(); this.poZmene(); }))
        .addButton((b) => b.setButtonText(T("Zálohovat sem")).setCta().onClick(() => hotovo(false)));
    }
  }

  onClose() {
    this.contentEl.empty();
  }
}

class MaterialVyber extends FuzzySuggestModal {
  constructor(plugin, poVyberu = null, vyzva = null) {
    super(plugin.app);
    this.plugin = plugin;
    this.poVyberu = poVyberu;
    this.setPlaceholder(vyzva || T("Který materiál jsi zpracoval ručně?"));
  }
  getItems() {
    try {
      return JSON.parse(fs.readFileSync(path.join(this.plugin.zaklad, "_Systém", "fronta.json"), "utf8"));
    } catch (e) {
      return [];
    }
  }
  getItemText(m) {
    return m.soubor;
  }
  async onChooseItem(m) {
    if (this.poVyberu) return this.poVyberu(m);
    try {
      await this.plugin.spustPython("priprav.py", ["--hotovo", m.soubor]);
      await this.plugin.spustPython("priprav.py", []);
      new Notice(T("✔️ Označeno jako zpracované: {0}", m.soubor));
    } catch (e) {
      this.plugin.chyba(T("Nepodařilo se označit: {0}", e.message), "rucne-hotovo");
    }
  }
}

class PredmetVyber extends FuzzySuggestModal {
  constructor(plugin, poVyberu) {
    super(plugin.app);
    this.plugin = plugin;
    this.poVyberu = poVyberu;
    this.setPlaceholder(T("Vyber předmět…"));
  }
  getItems() {
    return this.plugin.predmety();
  }
  getItemText(p) {
    return `${p.kod} ${p.nazev}`.trim();
  }
  onChooseItem(p) {
    this.poVyberu(p);
  }
}
