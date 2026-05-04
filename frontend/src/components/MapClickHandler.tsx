import { useMapEvents } from "react-leaflet";

type MapClickHandlerProps = {
  onClick: (lat: number, lng: number) => Promise<void>;
};

function MapClickHandler({ onClick}: MapClickHandlerProps) {
  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng;
      onClick(lat, lng);
    },
  });

  return null;
}

export default MapClickHandler;