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
  posterTitle: "Penyal d'Ifac 3D",
  loadingRoute: "Cargando el recorrido…",
  loadingProgress: "Progreso de la carga",
  loadingTerrain: "Cargando el terreno…",
  terrainReady: "Terreno visible. Preparando el paseo…",
  walkReady: "Listo. Ya puedes caminar.",
  terrainMissing: "Terreno en preparación",
  terrainFailed: "El terreno no está disponible.",
  routeDataFailed: "No se pudieron cargar los datos del recorrido.",
  tunnelMissing: "El interior del túnel no está disponible.",
  tunnelFailed: "El túnel no está disponible.",
  startFailed: "Error al iniciar el Penyal d'Ifac 3D.",
  autowalkFailed: "No se puede iniciar el paseo automático.",
  hintKeyboard: "W A S D para andar · ← → para girar · Mayús para correr",
  hintTouch: "Arrastra a la izquierda para andar y a la derecha para mirar",
  corridorNotice: "Por tu seguridad y la del parque, no salgas del sendero.",
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
  posterTitle: "Penyal d'Ifac 3D",
  loadingRoute: "Carregant el recorregut…",
  loadingProgress: "Progrés de la càrrega",
  loadingTerrain: "Carregant el terreny…",
  terrainReady: "Terreny visible. Preparant el passeig…",
  walkReady: "Llest. Ja pots caminar.",
  terrainMissing: "Terreny en preparació",
  terrainFailed: "El terreny no està disponible.",
  routeDataFailed: "No s'han pogut carregar les dades del recorregut.",
  tunnelMissing: "L'interior del túnel no està disponible.",
  tunnelFailed: "El túnel no està disponible.",
  startFailed: "Error en iniciar el Penyal d'Ifac 3D.",
  autowalkFailed: "No es pot iniciar el passeig automàtic.",
  hintKeyboard: "W A S D per a caminar · ← → per a girar · Maj per a córrer",
  hintTouch: "Arrossega a l'esquerra per a caminar i a la dreta per a mirar",
  corridorNotice: "Per la teua seguretat i la del parc, no isques del sender.",
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
  posterTitle: "Penyal d'Ifac 3D",
  loadingRoute: "Loading the route…",
  loadingProgress: "Loading progress",
  loadingTerrain: "Loading the terrain…",
  terrainReady: "Terrain visible. Getting the walk ready…",
  walkReady: "Ready. You can walk now.",
  terrainMissing: "Terrain in preparation",
  terrainFailed: "The terrain is not available.",
  routeDataFailed: "The route data could not be loaded.",
  tunnelMissing: "The tunnel interior is not available.",
  tunnelFailed: "The tunnel is not available.",
  startFailed: "Penyal d'Ifac 3D failed to start.",
  autowalkFailed: "The automatic walk cannot start.",
  hintKeyboard: "W A S D to walk · ← → to turn · Shift to run",
  hintTouch: "Drag on the left to walk and on the right to look",
  corridorNotice: "For your safety and the park's, please stay on the trail.",
};

export const STRINGS: Readonly<Record<Locale, StringTable>> = { es, va, en };

export function t(key: StringKey, locale: Locale = DEFAULT_LOCALE): string {
  return STRINGS[locale][key];
}
