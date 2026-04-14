import { Outlet, Link, useLocation, useNavigate } from "react-router";
import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Upload,
  CheckCircle,
  Map as MapIcon,
  ClipboardCheck,
  Database,
  Leaf,
  ChevronRight,
  Menu,
  X,
  Bell,
  HelpCircle,
  Layers,
} from "lucide-react";
import clsx from "clsx";

const steps = [
  { name: "Upload & Extract", shortName: "Upload",  path: "/",             icon: Upload,        description: "Import supplier documents"    },
  { name: "ABN Enrichment",   shortName: "Enrich",  path: "/enrichment",   icon: Database,      description: "Validate against ABR"         },
  { name: "Map & Review",     shortName: "Review",  path: "/review",       icon: ClipboardCheck, description: "Locate, review & approve"    },
  { name: "Biodiversity GIS", shortName: "BioRisk", path: "/biodiversity", icon: Layers,        description: "GIS overlay & risk profile"   },
];

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const currentStepIdx = steps.findIndex((s) => s.path === location.pathname);

  return (
    <div className="min-h-screen bg-slate-50 flex" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex w-[260px] flex-col bg-white border-r border-slate-200 fixed inset-y-0 left-0 z-40">
        {/* Logo */}
        <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-100">
          <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
            <Leaf className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg tracking-tight text-slate-900" style={{ fontWeight: 600 }}>EcoTrace</span>
          <span className="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-100">Beta</span>
        </div>

        {/* Nav Steps */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest px-2 mb-3">Workflow</p>
          {steps.map((step, idx) => {
            const isActive = location.pathname === step.path;
            const isCompleted = idx < currentStepIdx;
            const Icon = step.icon;
            return (
              <Link
                key={step.path}
                to={step.path}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all group",
                  isActive
                    ? "bg-emerald-50 text-emerald-700"
                    : isCompleted
                    ? "text-slate-600 hover:bg-slate-50"
                    : "text-slate-400 hover:bg-slate-50 hover:text-slate-600"
                )}
              >
                <div
                  className={clsx(
                    "w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                    isActive
                      ? "bg-emerald-600 text-white"
                      : isCompleted
                      ? "bg-emerald-100 text-emerald-600"
                      : "bg-slate-100 text-slate-400 group-hover:bg-slate-200"
                  )}
                >
                  {isCompleted ? <CheckCircle className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className={clsx("text-[13px] font-medium leading-tight", isActive ? "text-emerald-700" : "")}>
                    {step.name}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate mt-0.5">{step.description}</div>
                </div>
                {isActive && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="px-3 py-4 border-t border-slate-100 space-y-0.5">
          <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm text-slate-500 hover:bg-slate-50 hover:text-slate-700 transition-all">
            <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center">
              <HelpCircle className="w-3.5 h-3.5" />
            </div>
            <span className="text-[13px]">Help &amp; docs</span>
          </button>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/30 z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-[260px] bg-white border-r border-slate-200 z-50 flex flex-col"
            >
              <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-100">
                <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
                  <Leaf className="w-4 h-4 text-white" />
                </div>
                <span className="text-lg font-semibold tracking-tight text-slate-900">EcoTrace</span>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="ml-auto p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <nav className="flex-1 px-3 py-4 space-y-0.5">
                {steps.map((step, idx) => {
                  const isActive = location.pathname === step.path;
                  const isCompleted = idx < currentStepIdx;
                  const Icon = step.icon;
                  return (
                    <Link
                      key={step.path}
                      to={step.path}
                      onClick={() => setSidebarOpen(false)}
                      className={clsx(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all",
                        isActive ? "bg-emerald-50 text-emerald-700" : "text-slate-500 hover:bg-slate-50"
                      )}
                    >
                      <div
                        className={clsx(
                          "w-7 h-7 rounded-lg flex items-center justify-center shrink-0",
                          isActive ? "bg-emerald-600 text-white" : isCompleted ? "bg-emerald-100 text-emerald-600" : "bg-slate-100 text-slate-400"
                        )}
                      >
                        {isCompleted ? <CheckCircle className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                      </div>
                      <span className="text-[13px] font-medium">{step.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main content area */}
      <div className="flex-1 flex flex-col lg:pl-[260px] h-screen">
        {/* Top header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 lg:px-6 gap-4 sticky top-0 z-30 shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Step breadcrumb */}
          <div className="hidden lg:flex items-center gap-1.5 text-sm">
            {steps.map((step, idx) => {
              const isActive = location.pathname === step.path;
              return (
                <div key={step.path} className="flex items-center gap-1.5">
                  {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-300" />}
                  <button
                    onClick={() => navigate(step.path)}
                    className={clsx(
                      "px-2.5 py-1 rounded-lg text-[12px] font-medium transition-colors",
                      isActive
                        ? "bg-emerald-50 text-emerald-700"
                        : idx < currentStepIdx
                        ? "text-slate-600 hover:bg-slate-100"
                        : "text-slate-400"
                    )}
                  >
                    {step.shortName}
                  </button>
                </div>
              );
            })}
          </div>

          {/* Mobile: current step */}
          <div className="lg:hidden flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-800">
              {steps[currentStepIdx]?.name ?? "EcoTrace"}
            </span>
          </div>

          {/* Right side actions */}
          <div className="ml-auto flex items-center gap-2">
            <button className="relative p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
            </button>
            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
              <span className="text-[12px] font-semibold text-emerald-700">AL</span>
            </div>
          </div>
        </header>

        {/* Page content — flex-1 flex-col overflow-hidden so children with
            flex-1/min-h-0 (BiodiversityPage, MapPage) receive a resolved height.
            Pages that need internal scroll must manage it themselves. */}
        <main className="flex-1 flex flex-col overflow-hidden p-4 lg:p-6 min-h-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
