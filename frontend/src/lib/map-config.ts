export interface MapTileConfig { url: string; attribution: string }

const providers: Record<string, MapTileConfig> = {
  osm: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  carto: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
};

export function mapTileConfig(provider = process.env.NEXT_PUBLIC_MAP_TILE_PROVIDER ?? "osm"): MapTileConfig {
  const config = providers[provider];
  if (!config) throw new Error("NEXT_PUBLIC_MAP_TILE_PROVIDER must be osm or carto");
  return config;
}
