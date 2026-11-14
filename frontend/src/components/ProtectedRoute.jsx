import { Link, Navigate, useLocation } from "react-router-dom";
import { ShieldAlert, ArrowRight, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ requiredRole, allowedRoles, children }) {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-16">
        <div className="rounded-2xl border border-navy-900/10 bg-white p-10 text-center shadow-sm">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-navy-950 border-t-transparent" />
          <p className="text-sm font-medium text-navy-900/70">Verifying secure session...</p>
        </div>
      </div>
    );
  }

  const roles = allowedRoles || (requiredRole ? [requiredRole] : []);
  const isAdminRequired = roles.includes("ADMIN") && roles.length === 1;

  if (!user) {
    const loginPath = isAdminRequired ? "/admin/login" : "/login";
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  const hasAccess = roles.length === 0 || roles.includes(user.role) || user.role === "ADMIN";

  if (!hasAccess) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <div className="rounded-2xl border border-amber-200 bg-white p-8 shadow-sm">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-navy-950">
            {isAdminRequired ? "Administrator Privileges Required" : "Restricted Console Area"}
          </h1>
          <p className="mt-2 text-sm text-navy-900/75">
            You are currently signed in as <span className="font-semibold">{user.email}</span> (
            <span className="font-mono text-xs">{user.role}</span>). This section is restricted to{" "}
            <span className="font-semibold">{roles.join(" or ")}</span> accounts.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to={user.role === "ADMIN" ? "/admin" : "/dashboard"}
              className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-800"
            >
              <span>Go to {user.role === "ADMIN" ? "Admin Console" : "My Dashboard"}</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-2 rounded-xl border border-navy-900/15 bg-cream-50 px-4 py-2.5 text-sm font-semibold text-navy-950 transition hover:bg-cream-100"
            >
              <LogOut className="h-4 w-4" />
              <span>Sign out &amp; switch account</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return children;
}
