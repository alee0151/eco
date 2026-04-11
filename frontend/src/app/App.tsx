import { RouterProvider } from "react-router";
import { router } from "./routes";
import { SupplierProvider } from "./context/SupplierContext";
import { Toaster } from "sonner";

export default function App() {
  return (
    <SupplierProvider>
      <RouterProvider router={router} />
      <Toaster position="top-right" />
    </SupplierProvider>
  );
}
