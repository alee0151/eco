import BiodiversityDashboard from "../components/epic2/BiodiversityDashboard";

export function BiodiversityPage() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        top: '4rem',   /* below the fixed topbar (h-16) */
        left: '260px', /* beside the fixed sidebar on desktop */
      }}
      className="lg:block hidden"
    >
      <BiodiversityDashboard />
    </div>
  );
}
