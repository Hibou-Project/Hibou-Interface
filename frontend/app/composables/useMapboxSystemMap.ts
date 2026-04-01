import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useResizeObserver } from '@vueuse/core'
import { mapStyleUrl } from '~/lib/mapboxStyles'
import type { SystemSettings } from '~/types/settings'

const CENTER_SOURCE_ID = 'system-center'
const CENTER_LAYER_ID = 'system-center-circle'
const BEARING_LINE_SOURCE_ID = 'system-bearing-line'
const BEARING_LINE_LAYER_ID = 'system-bearing-line-line'
const DRONE_LINE_SOURCE_ID = 'system-drone-line'
const DRONE_LINE_LAYER_ID = 'system-drone-line-line'
const DRONE_CONE_SOURCE_ID = 'system-drone-cone'
const DRONE_CONE_LAYER_ID = 'system-drone-cone-fill'
const BUILDINGS_3D_LAYER_ID = 'system-3d-buildings'

/** Line length from center toward `bearingDeg` (degrees clockwise from north). */
const BEARING_LINE_LENGTH_M = 50

/** Drone spoke uses the same reach; cone fill uses the same radius. */
const DRONE_CONE_RADIUS_M = 75

/** Half of the cone aperture (degrees each side of `droneBearingDeg`). */
const DRONE_CONE_HALF_ANGLE_DEG = 18

/** Arc segments along the outer edge of the cone polygon. */
const DRONE_CONE_ARC_STEPS = 24

const DEFAULT_CENTER: [number, number] = [2.3522, 48.8566]
const DEFAULT_ZOOM = 10

/** Great-circle destination: bearing in degrees from north, distance in meters. Returns [lng, lat]. */
function destinationLngLat(
  lng: number,
  lat: number,
  bearingDeg: number,
  distanceM: number
): [number, number] {
  const R = 6371000
  const delta = distanceM / R
  const theta = (bearingDeg * Math.PI) / 180
  const phi1 = (lat * Math.PI) / 180
  const lambda1 = (lng * Math.PI) / 180

  const sinPhi1 = Math.sin(phi1)
  const cosPhi1 = Math.cos(phi1)
  const sinDelta = Math.sin(delta)
  const cosDelta = Math.cos(delta)

  const sinPhi2 = sinPhi1 * cosDelta + cosPhi1 * sinDelta * Math.cos(theta)
  const phi2 = Math.asin(sinPhi2)
  const lambda2 =
    lambda1 + Math.atan2(Math.sin(theta) * sinDelta * cosPhi1, cosDelta - sinPhi1 * sinPhi2)
  const lng2 = (((lambda2 * 180) / Math.PI + 540) % 360) - 180
  const lat2 = (phi2 * 180) / Math.PI
  return [lng2, lat2]
}

/** Closed ring: center → arc at `radiusM` from `centerBearing - halfAngle` to `centerBearing + halfAngle` → center. */
function coneSectorRing(
  lng: number,
  lat: number,
  centerBearingDeg: number,
  halfAngleDeg: number,
  radiusM: number,
  arcSteps: number
): [number, number][] {
  const ring: [number, number][] = [[lng, lat]]
  const start = centerBearingDeg - halfAngleDeg
  const end = centerBearingDeg + halfAngleDeg
  const step = arcSteps > 0 ? (end - start) / arcSteps : 0
  for (let i = 0; i <= arcSteps; i++) {
    const brg = start + step * i
    ring.push(destinationLngLat(lng, lat, brg, radiusM))
  }
  ring.push([lng, lat])
  return ring
}

type MapView = { lat: number; lng: number; zoom: number; pitch: number }

function mapViewFromSettings(s: SystemSettings | null | undefined): MapView | null {
  if (!s || s.latitude === undefined || s.longitude === undefined || s.map_zoom === undefined) {
    return null
  }
  let pitch = 0
  if (s.map_pitch !== undefined && Number.isFinite(s.map_pitch)) {
    pitch = Math.min(85, Math.max(0, s.map_pitch))
  }
  return {
    lat: s.latitude,
    lng: s.longitude,
    zoom: s.map_zoom,
    pitch,
  }
}

function applyMapViewCamera(map: mapboxgl.Map, v: MapView) {
  map.jumpTo({ center: [v.lng, v.lat], zoom: v.zoom, pitch: v.pitch, bearing: map.getBearing() })
}

/** Insert 3D buildings below the first symbol layer so labels stay readable. */
function findLayerIdBeforeFirstSymbol(map: mapboxgl.Map): string | undefined {
  const layers = map.getStyle()?.layers
  if (!layers) return undefined
  for (const layer of layers) {
    if (layer.type === 'symbol') {
      const layout = layer.layout
      if (layout && 'text-field' in layout && layout['text-field'] !== undefined) {
        return layer.id
      }
    }
  }
  return undefined
}

function remove3dBuildingsLayer(map: mapboxgl.Map) {
  if (map.getLayer(BUILDINGS_3D_LAYER_ID)) {
    map.removeLayer(BUILDINGS_3D_LAYER_ID)
  }
}

function add3dBuildingsLayer(map: mapboxgl.Map) {
  if (map.getLayer(BUILDINGS_3D_LAYER_ID) || !map.getSource('composite')) return
  const beforeId = findLayerIdBeforeFirstSymbol(map)
  const layer: mapboxgl.AnyLayer = {
    id: BUILDINGS_3D_LAYER_ID,
    type: 'fill-extrusion',
    source: 'composite',
    'source-layer': 'building',
    filter: ['==', 'extrude', 'true'],
    minzoom: 15,
    paint: {
      'fill-extrusion-color': '#9ca3af',
      'fill-extrusion-height': [
        'interpolate',
        ['linear'],
        ['zoom'],
        15,
        0,
        15.05,
        ['get', 'height'],
      ],
      'fill-extrusion-base': ['get', 'min_height'],
      'fill-extrusion-opacity': 0.65,
    },
  }
  try {
    if (beforeId) map.addLayer(layer, beforeId)
    else map.addLayer(layer)
  } catch {
    /* Style has no `building` source-layer */
  }
}

export function useMapboxSystemMap(
  containerRef: Ref<HTMLDivElement | null | undefined>,
  options: {
    accessToken: Ref<string>
    enabled: Ref<boolean>
    settings: Ref<SystemSettings | null | undefined>
    /** Degrees clockwise from north; line is drawn from system center along this bearing. */
    bearingDeg: Ref<number>
    /** Drone heading: spoke + filled cone (sector) from center along this bearing. */
    droneBearingDeg: Ref<number | null>
  }
) {
  const { accessToken, enabled, settings, bearingDeg, droneBearingDeg } = options
  const mapInstance = shallowRef<mapboxgl.Map | null>(null)
  /** Tracks applied style so `setStyle` only runs when the URL changes. */
  const lastAppliedStyleUrl = ref<string | null>(null)
  const mapView = computed(() => mapViewFromSettings(settings.value))

  function clearCenterCircleData(map: mapboxgl.Map) {
    const src = map.getSource(CENTER_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    if (src) {
      src.setData({ type: 'FeatureCollection', features: [] })
    }
  }

  function clearBearingLineData(map: mapboxgl.Map) {
    const src = map.getSource(BEARING_LINE_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    if (src) {
      src.setData({ type: 'FeatureCollection', features: [] })
    }
  }

  function clearDroneLineData(map: mapboxgl.Map) {
    const src = map.getSource(DRONE_LINE_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    if (src) {
      src.setData({ type: 'FeatureCollection', features: [] })
    }
  }

  function clearDroneConeData(map: mapboxgl.Map) {
    const src = map.getSource(DRONE_CONE_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    if (src) {
      src.setData({ type: 'FeatureCollection', features: [] })
    }
  }

  /**
   * Bottom → top: drone cone fill, bearing line, drone line, center circle.
   */
  function ensureOverlayLayers(map: mapboxgl.Map) {
    if (!map.getSource(DRONE_CONE_SOURCE_ID)) {
      map.addSource(DRONE_CONE_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: DRONE_CONE_LAYER_ID,
        type: 'fill',
        source: DRONE_CONE_SOURCE_ID,
        paint: {
          'fill-color': '#22d3ee',
          'fill-opacity': 0.22,
          'fill-outline-color': '#22d3ee',
        },
      })
    }
    if (!map.getSource(BEARING_LINE_SOURCE_ID)) {
      map.addSource(BEARING_LINE_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: BEARING_LINE_LAYER_ID,
        type: 'line',
        source: BEARING_LINE_SOURCE_ID,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#ffffff',
          'line-width': 3,
          'line-opacity': 0.92,
        },
      })
    }
    if (!map.getSource(DRONE_LINE_SOURCE_ID)) {
      map.addSource(DRONE_LINE_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: DRONE_LINE_LAYER_ID,
        type: 'line',
        source: DRONE_LINE_SOURCE_ID,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': '#22d3ee',
          'line-width': 4,
          'line-opacity': 0.95,
        },
      })
    }
    if (!map.getSource(CENTER_SOURCE_ID)) {
      map.addSource(CENTER_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: CENTER_LAYER_ID,
        type: 'circle',
        source: CENTER_SOURCE_ID,
        paint: {
          'circle-radius': 10,
          'circle-color': '#f43f5e',
          'circle-opacity': 0.92,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        },
      })
    }
  }

  function setCenterCircle(map: mapboxgl.Map, lng: number, lat: number) {
    ensureOverlayLayers(map)
    const src = map.getSource(CENTER_SOURCE_ID) as mapboxgl.GeoJSONSource
    src.setData({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: {},
    })
  }

  function setBearingLine(map: mapboxgl.Map, lng: number, lat: number, bearing: number) {
    ensureOverlayLayers(map)
    const [endLng, endLat] = destinationLngLat(lng, lat, bearing, BEARING_LINE_LENGTH_M)
    const src = map.getSource(BEARING_LINE_SOURCE_ID) as mapboxgl.GeoJSONSource
    src.setData({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [lng, lat],
          [endLng, endLat],
        ],
      },
      properties: {},
    })
  }

  function syncCenterCircle() {
    const map = mapInstance.value
    if (!map?.isStyleLoaded()) return
    const v = mapView.value
    if (!v) {
      clearCenterCircleData(map)
      return
    }
    setCenterCircle(map, v.lng, v.lat)
  }

  function syncBearingLine() {
    const map = mapInstance.value
    if (!map?.isStyleLoaded()) return
    const v = mapView.value
    if (!v) {
      clearBearingLineData(map)
      return
    }
    setBearingLine(map, v.lng, v.lat, bearingDeg.value)
  }

  function setDroneLine(map: mapboxgl.Map, lng: number, lat: number, bearing: number) {
    ensureOverlayLayers(map)
    const [endLng, endLat] = destinationLngLat(lng, lat, bearing, DRONE_CONE_RADIUS_M)
    const src = map.getSource(DRONE_LINE_SOURCE_ID) as mapboxgl.GeoJSONSource
    src.setData({
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: [
          [lng, lat],
          [endLng, endLat],
        ],
      },
      properties: {},
    })
  }

  function setDroneCone(map: mapboxgl.Map, lng: number, lat: number, centerBearing: number) {
    ensureOverlayLayers(map)
    const ring = coneSectorRing(
      lng,
      lat,
      centerBearing,
      DRONE_CONE_HALF_ANGLE_DEG,
      DRONE_CONE_RADIUS_M,
      DRONE_CONE_ARC_STEPS
    )
    const src = map.getSource(DRONE_CONE_SOURCE_ID) as mapboxgl.GeoJSONSource
    src.setData({
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [ring],
      },
      properties: {},
    })
  }

  function syncDroneOverlays() {
    const map = mapInstance.value
    if (!map?.isStyleLoaded()) return
    const v = mapView.value
    if (!v) {
      clearDroneLineData(map)
      clearDroneConeData(map)
      return
    }
    const b = droneBearingDeg.value
    if (!b) {
      clearDroneLineData(map)
      clearDroneConeData(map)
      return
    }
    setDroneCone(map, v.lng, v.lat, b)
    setDroneLine(map, v.lng, v.lat, b)
  }

  function sync3dBuildingsLayer() {
    const map = mapInstance.value
    if (!map?.isStyleLoaded()) return
    if (settings.value?.map_3d_buildings === true) {
      add3dBuildingsLayer(map)
    } else {
      remove3dBuildingsLayer(map)
    }
  }

  function resyncOverlaysAfterStyle() {
    const map = mapInstance.value
    const v = mapView.value
    if (map && v) {
      applyMapViewCamera(map, v)
    }
    sync3dBuildingsLayer()
    syncCenterCircle()
    syncBearingLine()
    syncDroneOverlays()
  }

  function syncFromSettings() {
    const map = mapInstance.value
    if (!map) return
    const v = mapView.value
    if (v) {
      applyMapViewCamera(map, v)
    }
    const styleUrl = mapStyleUrl(settings.value?.mapbox_style)
    if (lastAppliedStyleUrl.value !== styleUrl) {
      lastAppliedStyleUrl.value = styleUrl
      map.setStyle(styleUrl)
      map.once('style.load', resyncOverlaysAfterStyle)
      return
    }
    resyncOverlaysAfterStyle()
  }

  onMounted(() => {
    if (!enabled.value) return
    const el = containerRef.value
    if (!el) return

    mapboxgl.accessToken = accessToken.value
    const initialStyle = mapStyleUrl(settings.value?.mapbox_style)
    lastAppliedStyleUrl.value = initialStyle
    const initialView = mapViewFromSettings(settings.value)
    const map = new mapboxgl.Map({
      container: el,
      style: initialStyle,
      center: initialView ? { lng: initialView.lng, lat: initialView.lat } : DEFAULT_CENTER,
      zoom: initialView?.zoom ?? DEFAULT_ZOOM,
      pitch: initialView?.pitch ?? 0,
      attributionControl: false,
    })
    const logoControl = (map as unknown as { _logoControl?: mapboxgl.IControl })._logoControl
    if (logoControl) map.removeControl(logoControl)

    mapInstance.value = map

    map.on('load', () => {
      const v = mapView.value
      if (v) applyMapViewCamera(map, v)
      sync3dBuildingsLayer()
      syncCenterCircle()
      syncBearingLine()
      syncDroneOverlays()
    })

    nextTick(() => {
      requestAnimationFrame(() => map.resize())
    })
  })

  useResizeObserver(containerRef, () => {
    mapInstance.value?.resize()
  })

  onBeforeUnmount(() => {
    mapInstance.value?.remove()
    mapInstance.value = null
    lastAppliedStyleUrl.value = null
  })

  watch([settings, mapInstance], syncFromSettings, { immediate: true })
  watch(bearingDeg, syncBearingLine)
  watch(droneBearingDeg, syncDroneOverlays)

  return { syncFromSettings }
}
