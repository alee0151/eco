import { useNavigate } from "react-router";
import { MapPin } from "lucide-react";
import BiodiversityDashboard from "../components/epic2/BiodiversityDashboard";
import { useSuppliers } from "../context/SupplierContext";

export function BiodiversityPage() {
  const { suppliers, loading } = useSuppliers();
  const navigate = useNavigate();

  // Show a clear empty state if no supplier has geocoded coordinates yet.
  // Coordinates are only set after the user visits Map & Review (MapPage),
  // so navigating directly to /biodiversity would silently show nothing.
  const hasCoords = !loading && suppliers.some(s => s.coordinates);
  const hasSuppliers = !loading && suppliers.length > 0;

  if (!loading && hasSuppliers && !hasCoords) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
        <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center">
          <MapPin className="w-6 h-6 text-emerald-600" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-slate-800">Geocoding required</h2>
          <p className="text-sm text-slate-500 mt-1 max-w-xs">
            Supplier locations haven't been resolved yet. Visit{" "}
            <strong>Map &amp; Review</strong> to geocode your suppliers, then
            return here for biodiversity risk analysis.
          </p>
        </div>
        <button
          onClick={() => navigate("/review")}
          className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors"
        >
          Go to Map &amp; Review
        </button>
      </div>
    );
  }

  // Outer wrapper uses flex-1 flex flex-col min-h-0 instead of the old
  // h-[calc(100vh-7.5rem)]. Layout.tsx now makes <main> height-constrained
  // (flex-1 flex-col overflow-hidden), so flex-1 here resolves correctly
  // and the three-panel row inside BiodiversityDashboard gets a real height.
  return (
    <div className="flex-1 flex flex-col min-h-0 gap-4">
      <BiodiversityDashboard />
    </div>
  );
}
