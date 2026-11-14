import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Clock,
  Copy,
  CreditCard,
  ExternalLink,
  HelpCircle,
  Info,
  Loader2,
  Lock,
  QrCode,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Ticket,
  User,
  Wallet,
  XCircle,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { busApi } from "../services/api";

function formatCurrency(amount) {
  const num = Number(amount) || 0;
  return `₹${num.toFixed(2)}`;
}

export default function PaymentPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Try to load initial session data from location.state or sessionStorage
  const [sessionData, setSessionData] = useState(() => {
    if (location.state && location.state.transaction_ref) {
      return location.state;
    }
    try {
      const stored = sessionStorage.getItem("busreserve_payment_session");
      if (stored) return JSON.parse(stored);
    } catch {
      // ignore JSON parse error
    }
    return null;
  });

  const txnParam = searchParams.get("txn") || sessionData?.transaction_ref;

  // Server state tracking
  const [loadingOrder, setLoadingOrder] = useState(Boolean(txnParam && !sessionData));
  const [orderError, setOrderError] = useState("");
  const [orderData, setOrderData] = useState(null);

  // Payment form & selection state
  const [paymentMethod, setPaymentMethod] = useState("UPI");
  const [upiSubOption, setUpiSubOption] = useState("QR"); // "QR" | "ID"
  const [upiId, setUpiId] = useState("");
  const [selectedBank, setSelectedBank] = useState("HDFC");
  const [selectedWallet, setSelectedWallet] = useState("AMAZON_PAY");
  const [cardNumber, setCardNumber] = useState("4532 8920 1024 7712");
  const [cardExpiry, setCardExpiry] = useState("08/29");
  const [cardCvv, setCardCvv] = useState("458");
  const [cardName, setCardName] = useState(
    sessionData?.bookingPayload?.passenger_name || "Ananya Sharma"
  );

  // Simulation mode: "SUCCESS" | "FAIL_BANK" | "USER_CANCEL"
  const [simulationMode, setSimulationMode] = useState("SUCCESS");

  // Processing state
  const [processing, setProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [paymentStatus, setPaymentStatus] = useState("IDLE"); // "IDLE" | "SUCCESS" | "FAILED" | "CANCELLED"
  const [errorMessage, setErrorMessage] = useState("");
  const [errorCode, setErrorCode] = useState("");

  // Countdown timer (10 minutes)
  const [timeLeft, setTimeLeft] = useState(600);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Fetch or sync order details from backend if txnParam is present
  useEffect(() => {
    if (!txnParam) return;
    let active = true;

    async function fetchOrder() {
      try {
        setLoadingOrder(true);
        setOrderError("");
        const res = await busApi.getPaymentOrder(txnParam);
        if (!active) return;
        setOrderData(res);

        if (res.already_settled && res.booking?.pnr) {
          navigate(`/bookings/${res.booking.pnr}`, {
            state: { booking: res.booking, payment: res.transaction, justCreated: false },
            replace: true,
          });
          return;
        }

        if (res.transaction?.status === "FAILED") {
          setPaymentStatus("FAILED");
          setErrorCode(res.transaction.error_code || "PAYMENT_FAILED");
          setErrorMessage(res.transaction.error_message || "Transaction was failed.");
        } else if (res.transaction?.status === "CANCELLED") {
          setPaymentStatus("CANCELLED");
        }
      } catch (err) {
        if (!active) return;
        setOrderError(err.message || "Failed to load payment order details.");
      } finally {
        if (active) setLoadingOrder(false);
      }
    }

    fetchOrder();
    return () => {
      active = false;
    };
  }, [txnParam, navigate]);

  // Derived transaction details
  const transactionRef =
    orderData?.transaction?.transaction_ref ||
    sessionData?.transaction_ref ||
    txnParam;
  const orderId =
    orderData?.transaction?.gateway_order_id ||
    sessionData?.gateway_order_id ||
    orderData?.checkout?.order_id ||
    sessionData?.checkout?.order_id;
  const amount =
    orderData?.transaction?.amount ||
    sessionData?.amount ||
    sessionData?.bookingPayload?.fare ||
    850.0;
  const bookingPayload = sessionData?.bookingPayload || {};
  const trip = sessionData?.trip || {};
  const seat = sessionData?.seat || {};

  // Handle Card formatting
  const handleCardNumberChange = (e) => {
    const raw = e.target.value.replace(/\D/g, "").slice(0, 16);
    const formatted = raw.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
    setCardNumber(formatted);
  };

  const handleExpiryChange = (e) => {
    let raw = e.target.value.replace(/\D/g, "").slice(0, 4);
    if (raw.length >= 3) {
      raw = raw.slice(0, 2) + "/" + raw.slice(2);
    }
    setCardExpiry(raw);
  };

  // Payment Execution Handler
  const handleProceedPayment = async (e) => {
    e?.preventDefault();
    if (!transactionRef) {
      setErrorMessage("Missing transaction reference. Please restart booking.");
      return;
    }

    setProcessing(true);
    setErrorMessage("");
    setErrorCode("");

    // Simulate Case 1: USER_CANCEL
    if (simulationMode === "USER_CANCEL") {
      setProcessingStep(1);
      setTimeout(async () => {
        try {
          await busApi.cancelPayment({
            transaction_ref: transactionRef,
            reason: "User cancelled payment on checkout screen.",
          });
          setPaymentStatus("CANCELLED");
        } catch (err) {
          setPaymentStatus("CANCELLED");
        } finally {
          setProcessing(false);
        }
      }, 1000);
      return;
    }

    // Simulate Case 2: FAIL_BANK
    if (simulationMode === "FAIL_BANK") {
      setProcessingStep(1);
      setTimeout(() => setProcessingStep(2), 800);
      setTimeout(async () => {
        try {
          const failRes = await busApi.failPayment({
            transaction_ref: transactionRef,
            error_code: "BANK_DECLINED",
            error_message:
              "Card issuer or bank server declined the transaction (Simulated sandbox response code 51).",
          });
          setErrorCode("BANK_DECLINED");
          setErrorMessage(
            failRes.transaction?.error_message ||
              "Your bank was unable to authorize the transaction. No funds were debited."
          );
          setPaymentStatus("FAILED");
        } catch (err) {
          setErrorCode("GATEWAY_TIMEOUT");
          setErrorMessage(err.message || "Payment simulation encountered an error.");
          setPaymentStatus("FAILED");
        } finally {
          setProcessing(false);
        }
      }, 2000);
      return;
    }

    // Simulate Case 3: SUCCESS (Default)
    try {
      setProcessingStep(1); // Gateway Handshake
      await new Promise((r) => setTimeout(r, 600));

      setProcessingStep(2); // Cryptographic Signature
      await new Promise((r) => setTimeout(r, 600));

      setProcessingStep(3); // Atomic Seat Lock & Settlement
      const checkout = orderData?.checkout || sessionData?.checkout || {};
      const verifyResp = await busApi.verifyPayment({
        transaction_ref: transactionRef,
        gateway_payment_id:
          checkout.mock_payment_id || `PAY_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        gateway_signature:
          checkout.mock_signature || `mock_sig_${transactionRef}_${Date.now()}`,
        booking: bookingPayload,
      });

      setProcessingStep(4); // Ticket Generated
      await new Promise((r) => setTimeout(r, 400));

      // Clear session storage upon successful confirmation
      try {
        sessionStorage.removeItem("busreserve_payment_session");
      } catch {
        // ignore
      }

      setPaymentStatus("SUCCESS");
      navigate(`/bookings/${verifyResp.booking.pnr}`, {
        state: {
          booking: verifyResp.booking,
          payment: verifyResp.transaction || verifyResp.payment,
          justCreated: true,
        },
      });
    } catch (err) {
      setErrorCode(err.status === 409 ? "SEAT_CONFLICT" : "SETTLEMENT_ERROR");
      setErrorMessage(
        err.message ||
          "Cryptographic verification or atomic seat confirmation failed. Please try again."
      );
      setPaymentStatus("FAILED");
    } finally {
      setProcessing(false);
    }
  };

  // Retry Handler
  const handleRetryPayment = async () => {
    try {
      setProcessing(true);
      setErrorMessage("");
      setErrorCode("");
      await busApi.retryPayment(transactionRef);
      setPaymentStatus("IDLE");
      setSimulationMode("SUCCESS");
    } catch (err) {
      setErrorMessage(err.message || "Failed to reopen payment session.");
    } finally {
      setProcessing(false);
    }
  };

  // If no transaction session is available at all
  if (!loadingOrder && !transactionRef && !sessionData) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
          <AlertCircle className="h-7 w-7" />
        </div>
        <h1 className="font-display text-2xl font-bold text-navy-950">
          No Active Payment Session Found
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          We could not locate an active reservation session. This can happen if the
          session expired or the link is invalid.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            to="/search"
            className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-5 py-2.5 text-sm font-semibold text-white shadow-editorial transition hover:bg-emerald-700"
          >
            <ArrowLeft className="h-4 w-4" /> Search Available Buses
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF8F3] pb-20 pt-6">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* Navigation Breadcrumb & 256-Bit Encryption Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-navy-900/10 pb-4">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <Link to="/search" className="transition hover:text-navy-950">
              1. Search Buses
            </Link>
            <span>/</span>
            <span className="text-slate-500">2. Select Seats</span>
            <span>/</span>
            <span className="font-bold text-emerald-800">3. Secure Checkout</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800 border border-emerald-200">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
              256-Bit SSL Encrypted
            </span>
            <div className="flex items-center gap-1.5 rounded-full bg-navy-950/5 px-3 py-1 text-xs font-medium text-navy-950">
              <Clock className="h-3.5 w-3.5 text-amber-600" />
              Expires in:{" "}
              <span className="font-mono font-bold text-navy-900">
                {formatTimer(timeLeft)}
              </span>
            </div>
          </div>
        </div>

        {/* Main Grid: Left Payment Form / Right Journey & Fare Sidebar */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* LEFT COLUMN: Payment Methods & Sandbox Simulator (8 Cols) */}
          <div className="space-y-6 lg:col-span-8">
            {/* Payment Method Selector Card */}
            <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between border-b border-cream-200/80 pb-4">
                <div>
                  <h2 className="font-display text-lg font-bold text-navy-950">
                    Choose Payment Method
                  </h2>
                  <p className="text-xs text-slate-500">
                    Zero convenience fee applied. 100% verified sandbox transaction.
                  </p>
                </div>
                <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                  <Zap className="h-3 w-3" /> Instant Confirmation
                </div>
              </div>

              {/* Payment Tabs */}
              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  { id: "UPI", label: "UPI / QR", icon: QrCode, badge: "Most Popular" },
                  { id: "CARD", label: "Debit/Credit Card", icon: CreditCard, badge: "Instant" },
                  { id: "NETBANKING", label: "NetBanking", icon: Building2, badge: "All Banks" },
                  { id: "WALLET", label: "Wallets", icon: Wallet, badge: "Fast" },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const active = paymentMethod === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setPaymentMethod(tab.id)}
                      className={`relative flex flex-col items-center justify-center rounded-xl border p-3.5 text-center transition ${
                        active
                          ? "border-emerald-600 bg-emerald-50/70 text-navy-950 shadow-sm"
                          : "border-cream-200 bg-cream-50/40 text-slate-600 hover:border-navy-900/20 hover:bg-cream-100/50"
                      }`}
                    >
                      <Icon
                        className={`h-5 w-5 ${active ? "text-emerald-700" : "text-slate-500"}`}
                      />
                      <span className="mt-1.5 text-xs font-bold leading-tight">
                        {tab.label}
                      </span>
                      <span
                        className={`mt-1 text-[9px] font-medium px-1.5 py-0.2 rounded ${
                          active
                            ? "bg-emerald-200/60 text-emerald-900 font-semibold"
                            : "text-slate-400"
                        }`}
                      >
                        {tab.badge}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* TAB CONTENT: UPI */}
              {paymentMethod === "UPI" && (
                <div className="mt-6 rounded-xl border border-cream-200 bg-cream-50/40 p-4">
                  <div className="flex border-b border-cream-200 pb-3">
                    <button
                      type="button"
                      onClick={() => setUpiSubOption("QR")}
                      className={`mr-4 pb-1 text-xs font-bold transition ${
                        upiSubOption === "QR"
                          ? "border-b-2 border-emerald-600 text-emerald-900"
                          : "text-slate-500 hover:text-navy-950"
                      }`}
                    >
                      Scan Dynamic QR
                    </button>
                    <button
                      type="button"
                      onClick={() => setUpiSubOption("ID")}
                      className={`pb-1 text-xs font-bold transition ${
                        upiSubOption === "ID"
                          ? "border-b-2 border-emerald-600 text-emerald-900"
                          : "text-slate-500 hover:text-navy-950"
                      }`}
                    >
                      Enter Virtual Payment Address (VPA)
                    </button>
                  </div>

                  {upiSubOption === "QR" ? (
                    <div className="mt-4 flex flex-col items-center justify-center py-2 sm:flex-row sm:gap-8">
                      {/* Simulated QR Code box */}
                      <div className="relative flex h-44 w-44 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-emerald-600/40 bg-white p-3 shadow-inner">
                        <div className="grid grid-cols-6 gap-1 p-2 bg-navy-950 rounded-lg">
                          {[...Array(36)].map((_, i) => (
                            <div
                              key={i}
                              className={`h-4 w-4 rounded-xs ${
                                (i * 7 + 3) % 2 === 0
                                  ? "bg-white"
                                  : (i * 3) % 5 === 0
                                  ? "bg-emerald-400"
                                  : "bg-navy-950"
                              }`}
                            />
                          ))}
                        </div>
                        <span className="mt-2 text-[10px] font-bold text-navy-900">
                          Scan with any UPI App
                        </span>
                      </div>

                      <div className="mt-4 text-center sm:mt-0 sm:text-left">
                        <p className="text-xs font-bold text-navy-950">
                          Supported UPI Applications
                        </p>
                        <div className="mt-2 flex flex-wrap justify-center gap-2 sm:justify-start">
                          {["Google Pay", "PhonePe", "Paytm", "BHIM", "Cred"].map((app) => (
                            <span
                              key={app}
                              className="rounded-lg border border-cream-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-700 shadow-2xs"
                            >
                              {app}
                            </span>
                          ))}
                        </div>
                        <p className="mt-3 text-[11px] text-slate-500 max-w-xs">
                          Point your phone camera or open your favorite UPI app to scan and authorize {formatCurrency(amount)}.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 space-y-3">
                      <label className="block text-xs font-bold text-navy-900">
                        Enter UPI ID / VPA
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder="e.g. mobileNumber@upi or name@okaxis"
                          value={upiId}
                          onChange={(e) => setUpiId(e.target.value)}
                          className="flex-1 rounded-xl border border-navy-900/15 bg-white px-3.5 py-2.5 text-sm font-medium text-navy-950 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                        />
                        <button
                          type="button"
                          className="rounded-xl bg-emerald-700 px-4 py-2 text-xs font-bold text-white transition hover:bg-emerald-800"
                        >
                          Verify
                        </button>
                      </div>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {["@okhdfcbank", "@okicici", "@paytm", "@ybl", "@axl"].map((handle) => (
                          <button
                            key={handle}
                            type="button"
                            onClick={() => setUpiId((prev) => (prev.split("@")[0] || "user") + handle)}
                            className="rounded-md border border-cream-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-cream-100"
                          >
                            {handle}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB CONTENT: CARDS */}
              {paymentMethod === "CARD" && (
                <div className="mt-6 space-y-4 rounded-xl border border-cream-200 bg-cream-50/40 p-4">
                  <div>
                    <label className="block text-xs font-bold text-navy-900">
                      Card Number
                    </label>
                    <div className="relative mt-1">
                      <input
                        type="text"
                        maxLength={19}
                        value={cardNumber}
                        onChange={handleCardNumberChange}
                        placeholder="4532 8920 1024 7712"
                        className="w-full rounded-xl border border-navy-900/15 bg-white pl-10 pr-4 py-2.5 font-mono text-sm font-medium text-navy-950 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                      />
                      <CreditCard className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-navy-900">
                        Expiry Date (MM/YY)
                      </label>
                      <input
                        type="text"
                        maxLength={5}
                        value={cardExpiry}
                        onChange={handleExpiryChange}
                        placeholder="MM/YY"
                        className="mt-1 w-full rounded-xl border border-navy-900/15 bg-white px-3.5 py-2.5 font-mono text-sm font-medium text-navy-950 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-navy-900">
                        CVV / CVC
                      </label>
                      <input
                        type="password"
                        maxLength={4}
                        value={cardCvv}
                        onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, ""))}
                        placeholder="•••"
                        className="mt-1 w-full rounded-xl border border-navy-900/15 bg-white px-3.5 py-2.5 font-mono text-sm font-medium text-navy-950 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-navy-900">
                      Cardholder Name
                    </label>
                    <input
                      type="text"
                      value={cardName}
                      onChange={(e) => setCardName(e.target.value)}
                      placeholder="Name as printed on card"
                      className="mt-1 w-full rounded-xl border border-navy-900/15 bg-white px-3.5 py-2.5 text-sm font-medium text-navy-950 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                    />
                  </div>
                </div>
              )}

              {/* TAB CONTENT: NETBANKING */}
              {paymentMethod === "NETBANKING" && (
                <div className="mt-6 space-y-4 rounded-xl border border-cream-200 bg-cream-50/40 p-4">
                  <p className="text-xs font-bold text-navy-900">Popular Indian Banks</p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {[
                      { id: "HDFC", name: "HDFC Bank" },
                      { id: "SBI", name: "State Bank of India" },
                      { id: "ICICI", name: "ICICI Bank" },
                      { id: "AXIS", name: "Axis Bank" },
                    ].map((bank) => (
                      <button
                        key={bank.id}
                        type="button"
                        onClick={() => setSelectedBank(bank.id)}
                        className={`flex flex-col items-center justify-center rounded-xl border p-3 text-center transition ${
                          selectedBank === bank.id
                            ? "border-emerald-600 bg-white font-bold text-navy-950 shadow-sm"
                            : "border-cream-200 bg-white/60 text-slate-600 hover:bg-white"
                        }`}
                      >
                        <Building2 className="h-5 w-5 text-emerald-700" />
                        <span className="mt-1.5 text-xs">{bank.name}</span>
                      </button>
                    ))}
                  </div>

                  <div className="pt-2">
                    <label className="block text-xs font-bold text-navy-900">
                      Or Select From All Banks
                    </label>
                    <select
                      value={selectedBank}
                      onChange={(e) => setSelectedBank(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-navy-900/15 bg-white px-3.5 py-2.5 text-sm font-medium text-navy-950 focus:border-emerald-600 focus:outline-none"
                    >
                      <option value="HDFC">HDFC Bank</option>
                      <option value="SBI">State Bank of India</option>
                      <option value="ICICI">ICICI Bank</option>
                      <option value="AXIS">Axis Bank</option>
                      <option value="KOTAK">Kotak Mahindra Bank</option>
                      <option value="PNB">Punjab National Bank</option>
                      <option value="BOB">Bank of Baroda</option>
                      <option value="CANARA">Canara Bank</option>
                    </select>
                  </div>
                </div>
              )}

              {/* TAB CONTENT: WALLETS */}
              {paymentMethod === "WALLET" && (
                <div className="mt-6 space-y-4 rounded-xl border border-cream-200 bg-cream-50/40 p-4">
                  <p className="text-xs font-bold text-navy-900">Supported Digital Wallets</p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {[
                      { id: "AMAZON_PAY", name: "Amazon Pay" },
                      { id: "PAYTM_WALLET", name: "Paytm Wallet" },
                      { id: "PHONEPE_WALLET", name: "PhonePe" },
                      { id: "MOBIKWIK", name: "MobiKwik" },
                    ].map((w) => (
                      <button
                        key={w.id}
                        type="button"
                        onClick={() => setSelectedWallet(w.id)}
                        className={`flex flex-col items-center justify-center rounded-xl border p-3 text-center transition ${
                          selectedWallet === w.id
                            ? "border-emerald-600 bg-white font-bold text-navy-950 shadow-sm"
                            : "border-cream-200 bg-white/60 text-slate-600 hover:bg-white"
                        }`}
                      >
                        <Wallet className="h-5 w-5 text-emerald-700" />
                        <span className="mt-1.5 text-xs">{w.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Sandbox Outcome Simulator (Required by Acceptance Specification) */}
            <div className="rounded-2xl border border-amber-300/80 bg-gradient-to-br from-amber-50/60 to-cream-100/60 p-5 shadow-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-600 text-white">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-navy-950">
                      Sandbox Simulation Controller
                    </h3>
                    <p className="text-[11px] text-slate-600">
                      Test multi-scenario resilience without real financial debits
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900 border border-amber-200">
                  DEVELOPER MODE
                </span>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                <button
                  type="button"
                  onClick={() => setSimulationMode("SUCCESS")}
                  className={`flex items-start gap-2.5 rounded-xl border p-3 text-left transition ${
                    simulationMode === "SUCCESS"
                      ? "border-emerald-600 bg-white shadow-sm ring-1 ring-emerald-600"
                      : "border-amber-200/80 bg-white/70 hover:bg-white"
                  }`}
                >
                  <CheckCircle2
                    className={`mt-0.5 h-4 w-4 shrink-0 ${
                      simulationMode === "SUCCESS" ? "text-emerald-600" : "text-slate-400"
                    }`}
                  />
                  <div>
                    <p className="text-xs font-bold text-navy-950">Normal Success</p>
                    <p className="text-[10px] text-slate-500">
                      Settles instantly, issues confirmed PNR and ticket.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setSimulationMode("FAIL_BANK")}
                  className={`flex items-start gap-2.5 rounded-xl border p-3 text-left transition ${
                    simulationMode === "FAIL_BANK"
                      ? "border-red-600 bg-white shadow-sm ring-1 ring-red-600"
                      : "border-amber-200/80 bg-white/70 hover:bg-white"
                  }`}
                >
                  <XCircle
                    className={`mt-0.5 h-4 w-4 shrink-0 ${
                      simulationMode === "FAIL_BANK" ? "text-red-600" : "text-slate-400"
                    }`}
                  />
                  <div>
                    <p className="text-xs font-bold text-navy-950">Bank Decline</p>
                    <p className="text-[10px] text-slate-500">
                      Simulates gateway timeout or insufficient funds.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setSimulationMode("USER_CANCEL")}
                  className={`flex items-start gap-2.5 rounded-xl border p-3 text-left transition ${
                    simulationMode === "USER_CANCEL"
                      ? "border-amber-600 bg-white shadow-sm ring-1 ring-amber-600"
                      : "border-amber-200/80 bg-white/70 hover:bg-white"
                  }`}
                >
                  <AlertTriangle
                    className={`mt-0.5 h-4 w-4 shrink-0 ${
                      simulationMode === "USER_CANCEL" ? "text-amber-600" : "text-slate-400"
                    }`}
                  />
                  <div>
                    <p className="text-xs font-bold text-navy-950">User Cancel</p>
                    <p className="text-[10px] text-slate-500">
                      Simulates user abandoning the checkout window.
                    </p>
                  </div>
                </button>
              </div>
            </div>

            {/* Error or Cancellation Feedback Display */}
            {paymentStatus === "FAILED" && (
              <div className="rounded-2xl border border-red-200 bg-red-50/80 p-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-red-100 text-red-600">
                    <ShieldAlert className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-bold text-red-950">
                      Payment Authorization Failed
                    </h4>
                    <p className="mt-1 text-xs text-red-800">
                      {errorMessage ||
                        "The transaction could not be completed. Your payment method was not debited."}
                    </p>
                    {errorCode && (
                      <p className="mt-1.5 font-mono text-[11px] font-semibold text-red-700">
                        Error Code: {errorCode}
                      </p>
                    )}
                    <div className="mt-4 flex flex-wrap gap-2.5">
                      <button
                        type="button"
                        onClick={handleRetryPayment}
                        disabled={processing}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-red-800 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-red-900"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Retry Payment
                      </button>
                      <Link
                        to={trip.id ? `/trips/${trip.id}/seats` : "/search"}
                        className="inline-flex items-center gap-1.5 rounded-xl border border-red-300 bg-white px-4 py-2 text-xs font-semibold text-red-800 hover:bg-red-50"
                      >
                        Change Seat or Bus
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {paymentStatus === "CANCELLED" && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
                    <AlertTriangle className="h-5 w-5" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-bold text-amber-950">
                      Payment Session Cancelled
                    </h4>
                    <p className="mt-1 text-xs text-amber-800">
                      You have cancelled this checkout session. Your selected seat reservation has been released.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2.5">
                      <button
                        type="button"
                        onClick={handleRetryPayment}
                        disabled={processing}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-navy-950 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                        Re-open &amp; Try Again
                      </button>
                      <Link
                        to="/search"
                        className="inline-flex items-center gap-1.5 rounded-xl border border-amber-300 bg-white px-4 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-50"
                      >
                        Search Buses
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Pay Button Action */}
            {paymentStatus !== "FAILED" && paymentStatus !== "CANCELLED" && (
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={handleProceedPayment}
                  disabled={processing || timeLeft === 0}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl bg-emerald-700 px-6 py-4 text-base font-bold text-white shadow-editorial transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {processing ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      <span>Processing Verification &amp; Atomic Lock...</span>
                    </>
                  ) : (
                    <>
                      <Lock className="h-4 w-4" />
                      <span>Pay {formatCurrency(amount)} Securely</span>
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </>
                  )}
                </button>

                <div className="flex items-center justify-between px-2 text-[11px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                    Protected by BusReserve Shield Guarantee
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setSimulationMode("USER_CANCEL");
                      handleProceedPayment();
                    }}
                    className="text-slate-400 hover:text-red-600 transition"
                  >
                    Cancel Checkout
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: Journey, Passenger & Fare Summary Sidebar (4 Cols) */}
          <div className="space-y-5 lg:col-span-4">
            {/* Journey Summary Card */}
            <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm">
              <h3 className="font-display text-sm font-bold uppercase tracking-wider text-navy-900/70 border-b border-cream-200 pb-3">
                Journey Summary
              </h3>

              <div className="mt-3.5 space-y-3 text-xs">
                <div>
                  <p className="font-bold text-navy-950 text-sm">
                    {trip.bus_operator || "Intercity Express"}
                  </p>
                  <p className="text-slate-500 text-[11px]">
                    {trip.bus_type || "AC Sleeper (2+1)"} • Bus #{trip.bus_number || "KA-01-F-2026"}
                  </p>
                </div>

                <div className="rounded-xl bg-cream-50/70 p-3 border border-cream-200/80 space-y-2">
                  <div className="flex justify-between">
                    <div>
                      <p className="text-[10px] uppercase font-bold text-slate-400">From</p>
                      <p className="font-semibold text-navy-900">{trip.origin || "Origin City"}</p>
                      <p className="text-[10px] text-slate-500">{trip.boarding_stop || "Boarding Point"}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] uppercase font-bold text-slate-400">To</p>
                      <p className="font-semibold text-navy-900">{trip.destination || "Destination City"}</p>
                      <p className="text-[10px] text-slate-500">{trip.drop_stop || "Drop Point"}</p>
                    </div>
                  </div>
                  <div className="border-t border-dashed border-cream-200/90 pt-1.5 flex justify-between text-[11px]">
                    <span className="text-slate-500">Departure:</span>
                    <span className="font-mono font-semibold text-navy-950">
                      {trip.departure_time ? new Date(trip.departure_time).toLocaleDateString("en-IN", {
                        weekday: "short",
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      }) : "Upcoming"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between rounded-xl bg-emerald-50/60 p-3 border border-emerald-100">
                  <div className="flex items-center gap-2">
                    <Ticket className="h-4 w-4 text-emerald-700" />
                    <div>
                      <p className="text-[10px] uppercase font-bold text-emerald-900">Seat Number</p>
                      <p className="font-display font-bold text-navy-950 text-sm">
                        {seat.seat_number || bookingPayload.seat_number || "Seat Confirmed"}
                      </p>
                    </div>
                  </div>
                  <span className="rounded-full bg-emerald-200/70 px-2.5 py-0.5 text-[10px] font-bold text-emerald-900">
                    Held Exclusively
                  </span>
                </div>
              </div>

              {/* Passenger Info Card */}
              <div className="mt-4 border-t border-cream-200 pt-3 text-xs space-y-1.5">
                <p className="text-[10px] uppercase font-bold text-slate-400">Passenger Info</p>
                <p className="font-semibold text-navy-950 flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  {bookingPayload.passenger_name || cardName || "Guest Passenger"}
                </p>
                {bookingPayload.passenger_email && (
                  <p className="text-[11px] text-slate-500 truncate">
                    {bookingPayload.passenger_email}
                  </p>
                )}
                {bookingPayload.passenger_phone && (
                  <p className="text-[11px] text-slate-500">
                    +91 {bookingPayload.passenger_phone}
                  </p>
                )}
              </div>
            </div>

            {/* Fare Breakdown Card */}
            <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm space-y-3">
              <h3 className="font-display text-sm font-bold uppercase tracking-wider text-navy-900/70 border-b border-cream-200 pb-3">
                Fare Breakdown
              </h3>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Base Seat Fare</span>
                  <span className="font-mono font-semibold text-navy-900">{formatCurrency(amount)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Platform &amp; Service Fee</span>
                  <span className="font-mono text-emerald-700 font-bold">₹0.00 (Zero Fee)</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Applicable GST / Taxes</span>
                  <span className="font-mono text-slate-500 font-medium">Included</span>
                </div>

                <div className="border-t border-dashed border-cream-300 pt-2.5 flex items-baseline justify-between">
                  <span className="font-bold text-navy-950 text-sm">Total Payable</span>
                  <span className="font-display text-xl font-extrabold text-emerald-700">
                    {formatCurrency(amount)}
                  </span>
                </div>
              </div>

              {/* Transaction ID & Session Metadata */}
              <div className="rounded-xl bg-cream-50/70 p-2.5 border border-cream-200/70 text-[10px] text-slate-500 space-y-1">
                <div className="flex justify-between font-mono">
                  <span>TXN REF:</span>
                  <span className="font-bold text-navy-900 truncate max-w-[170px]">
                    {transactionRef || "TXN_PENDING"}
                  </span>
                </div>
                {orderId && (
                  <div className="flex justify-between font-mono">
                    <span>ORDER ID:</span>
                    <span className="truncate max-w-[170px]">{orderId}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Trust & Guarantee Badges */}
            <div className="rounded-2xl border border-cream-200/80 bg-cream-50/50 p-4 space-y-2 text-[11px] text-slate-600">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
                <span>100% Secure Payment processing</span>
              </div>
              <div className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-emerald-600 shrink-0" />
                <span>Instant refund upon cancellation</span>
              </div>
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-emerald-600 shrink-0" />
                <span>Cryptographic HMAC-SHA256 signature audit</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Processing Overlay */}
      {processing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/70 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl text-center space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 ring-8 ring-emerald-50/50">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>

            <div>
              <h3 className="font-display text-lg font-bold text-navy-950">
                Processing Secure Payment
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Please do not refresh or click the back button
              </p>
            </div>

            {/* Step-by-step progress checklist */}
            <div className="space-y-2.5 rounded-2xl bg-cream-50/70 p-4 text-left text-xs border border-cream-200/80">
              <div className="flex items-center gap-2.5">
                {processingStep >= 1 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-slate-300" />
                )}
                <span className={processingStep >= 1 ? "font-bold text-navy-950" : "text-slate-400"}>
                  Establishing secure gateway handshake
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                {processingStep >= 2 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-slate-300" />
                )}
                <span className={processingStep >= 2 ? "font-bold text-navy-950" : "text-slate-400"}>
                  Verifying SHA-256 cryptographic signature
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                {processingStep >= 3 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-slate-300" />
                )}
                <span className={processingStep >= 3 ? "font-bold text-navy-950" : "text-slate-400"}>
                  Acquiring atomic seat lock &amp; recording settlement
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                {processingStep >= 4 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-slate-300" />
                )}
                <span className={processingStep >= 4 ? "font-bold text-navy-950" : "text-slate-400"}>
                  Generating confirmed PNR &amp; issuing ticket
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
