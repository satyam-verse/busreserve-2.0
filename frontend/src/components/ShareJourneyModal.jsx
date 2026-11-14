import { useState } from "react";
import {
  AlertCircle,
  Check,
  Clock,
  Copy,
  ExternalLink,
  MessageCircle,
  Send,
  Share2,
  Shield,
  Trash2,
  X,
} from "lucide-react";
import { busApi } from "../services/api";

export default function ShareJourneyModal({ isOpen, onClose, booking }) {
  const [validityHours, setValidityHours] = useState(24);
  const [loading, setLoading] = useState(false);
  const storageKey = booking?.id ? `busreserve_share_${booking.id}` : null;
  const [shareData, setShareData] = useState(() => {
    if (!storageKey) return null;
    try {
      const saved = sessionStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed?.expires_at && new Date(parsed.expires_at) > new Date()) {
          return parsed;
        }
      }
    } catch {}
    return null;
  });
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [revoked, setRevoked] = useState(false);

  if (!isOpen || !booking) return null;

  const handleGenerateShare = async () => {
    setLoading(true);
    setError(null);
    setRevoked(false);
    try {
      const res = await busApi.createJourneyShare({
        booking_id: booking.id,
        validity_hours: Number(validityHours),
      });
      setShareData(res);
      if (storageKey) {
        try {
          sessionStorage.setItem(storageKey, JSON.stringify(res));
        } catch {}
      }
    } catch (err) {
      setError(err.message || "Failed to generate tracking share link.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = async () => {
    if (!shareData?.share_url) return;
    try {
      await navigator.clipboard.writeText(shareData.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleRevoke = async () => {
    if (!shareData?.token) return;
    if (!window.confirm("Are you sure you want to revoke this sharing link? Anyone with the link will immediately lose access.")) return;

    setRevoking(true);
    setError(null);
    try {
      await busApi.revokeJourneyShare(shareData.token);
      setRevoked(true);
      setShareData(null);
      if (storageKey) {
        try {
          sessionStorage.removeItem(storageKey);
        } catch {}
      }
    } catch (err) {
      setError(err.message || "Failed to revoke sharing link.");
    } finally {
      setRevoking(false);
    }
  };

  const shareText = `Track my BusReserve journey live: ${shareData?.share_url || ""}`;
  const whatsappUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
  const smsUrl = `sms:?body=${encodeURIComponent(shareText)}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-navy-950 px-6 py-4 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
              <Share2 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-display text-base font-bold text-white">
                Share Live Journey
              </h3>
              <p className="text-xs text-slate-300">
                PNR {booking.pnr} • {booking.trip?.source} → {booking.trip?.destination}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-2 text-slate-300 hover:bg-white/10 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Privacy Guarantee Pill */}
          <div className="flex items-start gap-3 rounded-xl bg-emerald-50 p-3.5 border border-emerald-200/80 text-emerald-950 text-xs">
            <Shield className="h-5 w-5 text-emerald-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Zero Personal Data Shared:</span>
              <p className="mt-0.5 text-emerald-800">
                Recipients can ONLY view the live bus location, route, and ETA on an interactive map. Your name, email, phone number, and ticket price are completely stripped and never exposed.
              </p>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-xl bg-red-50 p-3 text-xs font-medium text-red-700 border border-red-200">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {revoked && (
            <div className="flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-xs font-medium text-amber-800 border border-amber-200">
              <Check className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>Tracking link was revoked successfully. Any past links are now permanently inactive.</span>
            </div>
          )}

          {!shareData ? (
            /* Link Generation Form */
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-navy-900/70 mb-2">
                  Link Validity Duration
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[12, 24, 48, 72].map((hours) => (
                    <button
                      key={hours}
                      type="button"
                      onClick={() => setValidityHours(hours)}
                      className={`flex flex-col items-center justify-center rounded-xl p-3 text-xs font-bold border transition ${
                        validityHours === hours
                          ? "border-emerald-600 bg-emerald-50 text-emerald-800 shadow-xs"
                          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                      }`}
                    >
                      <Clock className="h-4 w-4 mb-1 text-slate-400" />
                      <span>{hours} Hours</span>
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleGenerateShare}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white shadow-md hover:bg-emerald-700 disabled:opacity-50 transition"
              >
                {loading ? (
                  <span>Generating Secure Token...</span>
                ) : (
                  <>
                    <Share2 className="h-4 w-4" />
                    <span>Create Live Sharing Link</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            /* Active Share Information & Sharing Channels */
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                  Secure Live Tracking Link
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={shareData.share_url}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 font-mono text-xs text-slate-800 select-all focus:outline-hidden"
                  />
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-navy-950 px-4 py-2.5 text-xs font-bold text-white hover:bg-navy-900 transition shrink-0 shadow-sm"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 text-emerald-400" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">
                  Link expires automatically on{" "}
                  {new Date(shareData.expires_at).toLocaleString([], {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </p>
              </div>

              {/* Instant Share Buttons */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-700 transition"
                >
                  <MessageCircle className="h-4 w-4" />
                  <span>WhatsApp</span>
                </a>
                <a
                  href={smsUrl}
                  className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-blue-700 transition"
                >
                  <Send className="h-4 w-4" />
                  <span>Send SMS</span>
                </a>
              </div>

              {/* Revoke Action */}
              <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                <a
                  href={shareData.share_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 hover:text-emerald-800 transition"
                >
                  <span>Preview Public Page</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
                <button
                  type="button"
                  onClick={handleRevoke}
                  disabled={revoking}
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-red-600 hover:bg-red-50 hover:text-red-700 transition"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>{revoking ? "Revoking..." : "Revoke Link"}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
