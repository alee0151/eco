import { useNavigate } from "react-router";
import { Upload } from "lucide-react";
import BiodiversityDashboard from "../components/epic2/BiodiversityDashboard";
import { useSuppliers } from "../context/SupplierContext";

export function BiodiversityPage() {
  const { suppliers, loading } = useSuppliers();
  const navigate = useNavigate();

  // Still initialising context (rare — context is synchronous, but guard anyway)
  if (loading) return null;

  // No suppliers uploaded yet — guide user to upload
  if (!loading && suppliers.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
        <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center">
          <Upload className="w-6 h-6 text-emerald-600" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-slate-800">No suppliers uploaded</h2>
          <p className="text-sm text-slate-500 mt-1 max-w-xs">
            Upload a supplier file first to begin biodiversity risk assessment.
          </p>
        </div>
        <button
          onClick={() => navigate("/upload")}
          className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors"
        >
          Go to Upload
        </button>
      </div>
    );
  }

  // Suppliers are present — show the dashboard immediately.
  // Supplier cards render right away; risk details (geocoding, DB queries)
  // load in the background with skeleton / loading states inside the panels.
  return (
    <div className="flex-1 flex flex-col min-h-0 gap-4">
      <BiodiversityDashboard />
    </div>
  );
}
