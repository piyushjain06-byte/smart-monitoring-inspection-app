import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { Link } from "react-router-dom";

const STATUS_COLOR = {
  PENDING: "#b5790a",
  OVERDUE: "#b23b3b",
  SUBMITTED: "#157a4a",
  NO_INSPECTION: "#7a8a99",
};

const STATUS_LABEL = {
  PENDING: "Inspection pending",
  OVERDUE: "Inspection overdue",
  SUBMITTED: "Last inspection submitted",
  NO_INSPECTION: "No inspection yet",
};

function dotIcon(color) {
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:14px;height:14px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 0 1px rgba(0,0,0,0.25)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export default function ProjectMap({ institutes }) {
  const withCoords = institutes.filter((i) => i.latitude != null && i.longitude != null);
  const center = withCoords.length
    ? [withCoords[0].latitude, withCoords[0].longitude]
    : [22.9734, 78.6569]; // fallback: roughly the center of India

  return (
    <MapContainer center={center} zoom={withCoords.length ? 6 : 4.5} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {withCoords.map((inst) => (
        <Marker
          key={inst.id}
          position={[inst.latitude, inst.longitude]}
          icon={dotIcon(STATUS_COLOR[inst.latest_inspection_status] || STATUS_COLOR.NO_INSPECTION)}
        >
          <Popup>
            <div className="text-sm">
              <div className="font-semibold">{inst.name}</div>
              <div className="text-[var(--ink-soft)]">{inst.district}, {inst.state}</div>
              <div className="mt-1">{STATUS_LABEL[inst.latest_inspection_status] || "Status unknown"}</div>
              <Link to={`/institutes/${inst.id}`} className="text-[var(--accent)] underline block mt-1">
                View details
              </Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
