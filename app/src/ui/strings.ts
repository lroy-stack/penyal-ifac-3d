/**
 * User-facing text, keyed by locale. Spanish is shown for now; Valencian and English are in
 * place so every key exists in all three (the Valencian text still needs the review planned for
 * the content phase). `index.html` takes its text from here at build time (`{{key}}`).
 */
export const LOCALES = ["es", "va", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "es";

const es = {
  pageTitle: "Penyal d'Ifac 3D",
  canvasLabel: "Vista 3D del Penyal d'Ifac",
  noscript:
    "Esta aplicación necesita JavaScript para mostrar el Penyal d'Ifac en 3D. Actívalo en tu navegador e inténtalo de nuevo.",
  attributionLine:
    "Datos: © Institut Cartogràfic Valencià (CC BY 4.0) · PNOA-LiDAR (CC BY 4.0 scne.es) · © colaboradores de OpenStreetMap (ODbL) · Texturas: Poly Haven (CC0)",
  creditsButton: "Créditos",
  creditsTitle: "Créditos y licencias",
  creditsClose: "Cerrar",
  creditsCode: "Código",
  creditsSources: "Datos y recursos",
  creditsApproximations: "Aproximaciones",
  creditsApproximationsNote:
    "Partes del modelo que no se basan en datos medidos. Los textos están en inglés, tal como figuran en CREDITS.md.",
  creditsSoftware: "Software de terceros",
  creditsLicence: "Licencia",
} as const;

export type StringKey = keyof typeof es;
export type StringTable = Readonly<Record<StringKey, string>>;

const va: StringTable = {
  pageTitle: "Penyal d'Ifac 3D",
  canvasLabel: "Vista 3D del Penyal d'Ifac",
  noscript:
    "Aquesta aplicació necessita JavaScript per a mostrar el Penyal d'Ifac en 3D. Activa'l en el teu navegador i torna-ho a provar.",
  attributionLine:
    "Dades: © Institut Cartogràfic Valencià (CC BY 4.0) · PNOA-LiDAR (CC BY 4.0 scne.es) · © col·laboradors d'OpenStreetMap (ODbL) · Textures: Poly Haven (CC0)",
  creditsButton: "Crèdits",
  creditsTitle: "Crèdits i llicències",
  creditsClose: "Tanca",
  creditsCode: "Codi",
  creditsSources: "Dades i recursos",
  creditsApproximations: "Aproximacions",
  creditsApproximationsNote:
    "Parts del model que no es basen en dades mesurades. Els textos són en anglés, tal com figuren en CREDITS.md.",
  creditsSoftware: "Programari de tercers",
  creditsLicence: "Llicència",
};

const en: StringTable = {
  pageTitle: "Penyal d'Ifac 3D",
  canvasLabel: "3D view of the Penyal d'Ifac",
  noscript:
    "This application needs JavaScript to show the Penyal d'Ifac in 3D. Turn it on in your browser and try again.",
  attributionLine:
    "Data: © Institut Cartogràfic Valencià (CC BY 4.0) · PNOA-LiDAR (CC BY 4.0 scne.es) · © OpenStreetMap contributors (ODbL) · Textures: Poly Haven (CC0)",
  creditsButton: "Credits",
  creditsTitle: "Credits and licences",
  creditsClose: "Close",
  creditsCode: "Code",
  creditsSources: "Data and assets",
  creditsApproximations: "Approximations",
  creditsApproximationsNote:
    "Parts of the model that are not based on measured data, as written in CREDITS.md.",
  creditsSoftware: "Third-party software",
  creditsLicence: "Licence",
};

export const STRINGS: Readonly<Record<Locale, StringTable>> = { es, va, en };

export function t(key: StringKey, locale: Locale = DEFAULT_LOCALE): string {
  return STRINGS[locale][key];
}
