import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { UploadExtractPage } from "./pages/UploadExtractPage";
import { EnrichmentPage } from "./pages/EnrichmentPage";
import { MapPage } from "./pages/MapPage";
import { BiodiversityPage } from "./pages/BiodiversityPage";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: UploadExtractPage },
      { path: "enrichment", Component: EnrichmentPage },
      { path: "review", Component: MapPage },
      { path: "biodiversity", Component: BiodiversityPage },
    ],
  },
]);
