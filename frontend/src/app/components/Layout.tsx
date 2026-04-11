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
} from "lucide-react";
import clsx from "clsx";

const steps = [
  { name: "Upload & Extract", shortName: "Upload", path: "/",           icon: Upload,       description: "Import supplier documents" },
  { name: "ABN Enrichment",   shortName: "Enrich", path: "/enrichment", icon: Database,     description: "Validate against ABR"     },
  { name: "Map & Review",     shortName: "Review", path: "/review",     icon: ClipboardCheck, description: "Locate, review & approve" },
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
          <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700" style={{ fontWeight: 600 }}>BETA</span>
        </div>

        {/* Workflow Steps */}
        <div className="flex-1 py-6 px-3 overflow-y-auto">
          <p className="text-[11px] uppercase tracking-widest text-slate-400 px-3 mb-4" style={{ fontWeight: 600 }}>Workflow</p>
          <nav className="space-y-1">
            {steps.map((step, idx) => {
              const isCurrent = location.pathname === step.path;
              const isPast = currentStepIdx > idx;

              return (
                <Link
                  key={step.path}
                  to={step.path}
                  className={clsx(
                    "group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all relative",
                    isCurrent
                      ? "bg-emerald-50 text-emerald-700"
                      : isPast
                      ? "text-slate-600 hover:bg-slate-50"
                      : "text-slate-400 hover:bg-slate-50 hover:text-slate-600"
                  )}
                >
                  <div
                    className={clsx(
                      "w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 transition-colors",
                      isCurrent
                        ? "bg-emerald-600 text-white"
                        : isPast
                        ? "bg-emerald-100 text-emerald-600"
                        : "bg-slate-100 text-slate-400"
                    )}
                  >
                    {isPast ? (
                      <CheckCircle className="w-3.5 h-3.5" />
                    ) : (
                      <step.icon className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className={clsx("truncate", isCurrent ? "text-emerald-700" : "")} style={{ fontWeight: isCurrent ? 600 : 500 }}>
                      {step.name}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate">{step.description}</p>
                  </div>
                  {isCurrent && (
                    <motion.div
                      layoutId="sidebar-indicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-emerald-600 rounded-r-full"
                      transition={{ type: "spring", stiffness: 350, damping: 30 }}
                    />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white text-xs" style={{ fontWeight: 600 }}>
              JD
            </div>
            <div className="min-w-0">
              <p className="text-sm text-slate-900 truncate" style={{ fontWeight: 500 }}>Jane Doe</p>
              <p className="text-xs text-slate-400 truncate">Compliance Analyst</p>
            </div>
          </div>
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
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 left-0 w-[260px] bg-white border-r border-slate-200 z-50 lg:hidden flex flex-col"
            >
              <div className="h-16 flex items-center justify-between px-5 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
                    <Leaf className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-lg tracking-tight text-slate-900" style={{ fontWeight: 600 }}>EcoTrace</span>
                </div>
                <button onClick={() => setSidebarOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="flex-1 py-6 px-3 overflow-y-auto">
                <p className="text-[11px] uppercase tracking-widest text-slate-400 px-3 mb-4" style={{ fontWeight: 600 }}>Workflow</p>
                <nav className="space-y-1">
                  {steps.map((step, idx) => {
                    const isCurrent = location.pathname === step.path;
                    const isPast = currentStepIdx > idx;
                    return (
                      <Link
                        key={step.path}
                        to={step.path}
                        onClick={() => setSidebarOpen(false)}
                        className={clsx(
                          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all",
                          isCurrent ? "bg-emerald-50 text-emerald-700" : isPast ? "text-slate-600" : "text-slate-400"
                        )}
                      >
                        <div
                          className={clsx(
                            "w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0",
                            isCurrent ? "bg-emerald-600 text-white" : isPast ? "bg-emerald-100 text-emerald-600" : "bg-slate-100 text-slate-400"
                          )}
                        >
                          {isPast ? <CheckCircle className="w-3.5 h-3.5" /> : <step.icon className="w-3.5 h-3.5" />}
                        </div>
                        <span style={{ fontWeight: isCurrent ? 600 : 500 }}>{step.name}</span>
                      </Link>
                    );
                  })}
                </nav>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main Area */}
      <div className="flex-1 lg:ml-[260px] flex flex-col min-h-screen">
        {/* Top Bar */}
        <header className="sticky top-0 z-30 h-14 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center px-4 lg:px-8 gap-4">
          <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-slate-500 hover:text-slate-700">
            <Menu className="w-5 h-5" />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm text-slate-400">
            <span>Supplier Intake</span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-slate-700" style={{ fontWeight: 500 }}>{steps[currentStepIdx >= 0 ? currentStepIdx : 0]?.name}</span>
          </div>

          {/* Step pills - desktop */}
          <div className="hidden md:flex items-center gap-1 ml-auto bg-slate-100 rounded-lg p-1">
            {steps.map((step, idx) => {
              const isCurrent = location.pathname === step.path;
              const isPast = currentStepIdx > idx;
              return (
                <button
                  key={step.path}
                  onClick={() => navigate(step.path)}
                  className={clsx(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all",
                    isCurrent
                      ? "bg-white text-emerald-700 shadow-sm"
                      : isPast
                      ? "text-emerald-600 hover:bg-white/50"
                      : "text-slate-400 hover:text-slate-600"
                  )}
                  style={{ fontWeight: isCurrent ? 600 : 500 }}
                >
                  {isPast ? <CheckCircle className="w-3 h-3" /> : <step.icon className="w-3 h-3" />}
                  {step.shortName}
                </button>
              );
            })}
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2 ml-auto md:ml-0">
            <button className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors">
              <HelpCircle className="w-4 h-4" />
            </button>
            <button className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors relative">
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-emerald-500 rounded-full" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}