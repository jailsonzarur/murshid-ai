import React, { useEffect, useState } from "react";

const THEME = {
  colors: {
    base: "#FFFFFF",
    ink: "#111111",
    muted: "rgba(17,17,17,0.68)",
    subtle: "rgba(17,17,17,0.52)",
    accent: "#976FED",
    accentStrong: "#7C3AED",
    accentDark: "#4C1D95",
    accentText: "#5B21B6",
    card: "rgba(255,255,255,0.78)",
    cardStrong: "rgba(255,255,255,0.92)",
    border: "rgba(17,17,17,0.10)",
    borderStrong: "rgba(17,17,17,0.16)",
    greenBg: "rgba(16,185,129,0.12)",
    greenText: "#065F46",
    blueBg: "rgba(14,165,233,0.12)",
    blueText: "#075985",
  },
};

const cn = (...classes) => classes.filter(Boolean).join(" ");

const iconPaths = {
  search: "M21 21l-4.35-4.35M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0",
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6l-.2.2a2 2 0 1 1-3.6 0L10 20a1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1l-.2-.2a2 2 0 1 1 0-3.6L4 10a1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6l.2-.2a2 2 0 1 1 3.6 0l.2.2a1.7 1.7 0 0 0 1 .6 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c.15.36.36.7.6 1l.2.2a2 2 0 1 1 0 3.6l-.2.2a1.7 1.7 0 0 0-.6 1Z",
  home: "M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-8.5Z",
  layers: "m12 3 9 5-9 5-9-5 9-5Zm-7.5 9L12 16l7.5-4M4.5 16 12 21l7.5-5",
  chart: "M4 19V5M4 19h17M8 16v-5M13 16V8M18 16v-9",
  users: "M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM21 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10ZM9 12l2 2 4-5",
  sparkles: "M12 3l1.7 5.1L19 10l-5.3 1.9L12 17l-1.7-5.1L5 10l5.3-1.9L12 3ZM5 15l.8 2.2L8 18l-2.2.8L5 21l-.8-2.2L2 18l2.2-.8L5 15ZM19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z",
  chevronDown: "m6 9 6 6 6-6",
  plus: "M12 5v14M5 12h14",
  filter: "M4 6h16M7 12h10M10 18h4",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  mail: "M4 6h16v12H4V6Zm0 1 8 6 8-6",
  lock: "M7 11V8a5 5 0 0 1 10 0v3M6 11h12v10H6V11Z",
  calendar: "M7 3v4M17 3v4M4 8h16M5 5h14v16H5V5Z",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  check: "M5 12l4 4L19 6",
  x: "M6 6l12 12M18 6 6 18",
  command: "M9 6a3 3 0 1 0-3 3h3V6Zm6 0v3h3a3 3 0 1 0-3-3ZM9 15H6a3 3 0 1 0 3 3v-3Zm6 0v3a3 3 0 1 0 3-3h-3ZM9 9h6v6H9V9Z",
  menu: "M4 7h16M4 12h16M4 17h16",
  arrowUpRight: "M7 17 17 7M9 7h8v8",
  creditCard: "M3 6h18v12H3V6Zm0 4h18M7 15h4",
  user: "M20 21a8 8 0 0 0-16 0M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z",
};

const navItems = [
  { label: "Dashboard", icon: "home", active: true },
  { label: "Components", icon: "layers" },
  { label: "Analytics", icon: "chart" },
  { label: "Customers", icon: "users" },
  { label: "Security", icon: "shield" },
  { label: "Settings", icon: "settings" },
];

function runDesignSystemTests() {
  const requiredIcons = [
    "search",
    "bell",
    "settings",
    "home",
    "layers",
    "chart",
    "users",
    "shield",
    "sparkles",
    "chevronDown",
    "plus",
    "filter",
    "more",
    "mail",
    "lock",
    "calendar",
    "upload",
    "check",
    "x",
    "command",
    "menu",
    "arrowUpRight",
    "creditCard",
    "user",
  ];

  console.assert(cn("a", false, "b", undefined, "c") === "a b c", "cn should remove falsy values");
  console.assert(requiredIcons.every((name) => typeof iconPaths[name] === "string" && iconPaths[name].length > 0), "all local icons should exist");
  console.assert(!Object.values(iconPaths).some((path) => path.includes("http")), "icons must not depend on remote URLs");
  console.assert(THEME.colors.base === "#FFFFFF" && THEME.colors.accent === "#976FED", "brand colors should remain unchanged");
  console.assert(/^#[0-9A-F]{6}$/i.test(THEME.colors.base), "base color should be normalized to six-digit hex");
  console.assert(/^#[0-9A-F]{6}$/i.test(THEME.colors.accent), "accent color should be normalized to six-digit hex");
  console.assert(navItems.length === 6, "sidebar should keep six navigation items");
  console.assert(THEME.colors.accentText === "#5B21B6", "input icons should have access to a dark purple contrast token");
  console.assert(iconPaths.mail.includes("M4 6h16v12"), "mail icon path should be present for form inputs");
  console.assert(iconPaths.lock.includes("M7 11V8"), "lock icon path should be present for form inputs");
  console.assert(iconPaths.calendar.includes("M7 3v4"), "calendar icon path should be present for form inputs");
}

function Icon({ name, className = "h-4 w-4", strokeWidth = 2, style = {}, ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
      {...props}
    >
      <path d={iconPaths[name] || iconPaths.sparkles} />
    </svg>
  );
}

function GlassPanel({ children, className = "", style = {} }) {
  return (
    <div
      className={cn("relative overflow-hidden rounded-3xl border backdrop-blur-2xl", className)}
      style={{
        background: "linear-gradient(135deg, rgba(255,255,255,0.86), rgba(255,255,255,0.58))",
        borderColor: THEME.colors.border,
        boxShadow: "0 20px 60px rgba(15,23,42,0.10), inset 0 1px 0 rgba(255,255,255,0.70)",
        ...style,
      }}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 rounded-3xl"
        style={{
          background: "linear-gradient(135deg, rgba(255,255,255,0.55), rgba(255,255,255,0.06) 45%, rgba(151,111,237,0.06))",
        }}
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
}

function Button({ children, variant = "primary", size = "md", className = "", icon }) {
  const variants = {
    primary: {
      background: THEME.colors.accent,
      borderColor: "rgba(151,111,237,0.62)",
      color: "#FFFFFF",
      boxShadow: "0 10px 24px rgba(151,111,237,0.24)",
    },
    secondary: {
      background: "rgba(255,255,255,0.96)",
      borderColor: THEME.colors.border,
      color: THEME.colors.ink,
      boxShadow: "0 8px 18px rgba(15,23,42,0.05)",
    },
    ghost: {
      background: "transparent",
      borderColor: "transparent",
      color: "rgba(17,17,17,0.78)",
      boxShadow: "none",
    },
    outline: {
      background: "transparent",
      borderColor: "rgba(151,111,237,0.62)",
      color: THEME.colors.accentText,
      boxShadow: "none",
    },
    dark: {
      background: THEME.colors.ink,
      borderColor: "rgba(17,17,17,0.18)",
      color: "#FFFFFF",
      boxShadow: "0 10px 24px rgba(17,17,17,0.16)",
    },
  };
  const sizes = {
    sm: "h-9 px-3 text-sm",
    md: "h-11 px-4 text-sm",
    lg: "h-13 px-6 text-base",
  };

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-2xl border font-medium transition-all duration-200 active:scale-95 focus:outline-none focus:ring-4",
        sizes[size],
        className
      )}
      style={{ ...variants[variant], outlineColor: "rgba(151,111,237,0.24)" }}
    >
      {icon && <Icon name={icon} className="h-4 w-4" />}
      {children}
    </button>
  );
}

function Field({ label, hint, error, icon, children }) {
  return (
    <label className="block space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium" style={{ color: "rgba(17,17,17,0.88)" }}>{label}</span>
        {hint && <span className="text-xs" style={{ color: THEME.colors.subtle }}>{hint}</span>}
      </div>
      <div className="relative">
        {icon && (
          <span
            className="pointer-events-none absolute left-3 top-1/2 z-20 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-lg"
            style={{ background: "rgba(151,111,237,0.10)", color: THEME.colors.accentText }}
          >
            <Icon name={icon} className="h-4 w-4" strokeWidth={2.35} />
          </span>
        )}
        {children}
      </div>
      {error && <p className="text-xs" style={{ color: THEME.colors.accentText }}>{error}</p>}
    </label>
  );
}

function Input({ placeholder, icon, error, value, type = "text" }) {
  return (
    <Field label={placeholder || "Input"} error={error} icon={icon}>
      <input
        type={type}
        defaultValue={value}
        placeholder={placeholder}
        className={cn("relative z-10 h-12 w-full rounded-2xl border px-4 text-sm outline-none backdrop-blur-xl transition", icon ? "pl-12" : "")}
        style={{
          background: "rgba(255,255,255,0.90)",
          borderColor: error ? "rgba(151,111,237,0.70)" : THEME.colors.border,
          color: THEME.colors.ink,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.75)",
        }}
      />
    </Field>
  );
}

function SelectBox({ label = "Select", value = "Choose option", options = [] }) {
  return (
    <Field label={label}>
      <button
        className="flex h-12 w-full items-center justify-between rounded-2xl border px-4 text-left text-sm backdrop-blur-xl transition"
        style={{ background: "rgba(255,255,255,0.90)", borderColor: THEME.colors.border, color: "rgba(17,17,17,0.82)" }}
      >
        <span>{value}</span>
        <Icon name="chevronDown" className="h-4 w-4" />
      </button>
      <div
        className="mt-2 rounded-2xl border p-2 shadow-2xl backdrop-blur-2xl"
        style={{ background: "rgba(246,242,255,0.92)", borderColor: THEME.colors.border }}
      >
        {options.map((option, index) => (
          <div
            key={option}
            className="flex items-center justify-between rounded-xl px-3 py-2 text-sm"
            style={{
              background: index === 0 ? "rgba(151,111,237,0.16)" : "transparent",
              color: index === 0 ? THEME.colors.accentDark : "rgba(17,17,17,0.72)",
            }}
          >
            {option}
            {index === 0 && <Icon name="check" className="h-4 w-4" style={{ color: THEME.colors.accent }} />}
          </div>
        ))}
      </div>
    </Field>
  );
}

function Badge({ children, tone = "orange" }) {
  const tones = {
    orange: { borderColor: "rgba(151,111,237,0.35)", background: "rgba(151,111,237,0.14)", color: THEME.colors.accentText },
    green: { borderColor: "rgba(16,185,129,0.22)", background: THEME.colors.greenBg, color: THEME.colors.greenText },
    blue: { borderColor: "rgba(14,165,233,0.22)", background: THEME.colors.blueBg, color: THEME.colors.blueText },
    neutral: { borderColor: THEME.colors.border, background: "rgba(255,255,255,0.88)", color: "rgba(17,17,17,0.78)" },
  };
  return (
    <span className="inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold" style={tones[tone]}>
      {children}
    </span>
  );
}

function Toggle({ checked = true }) {
  return (
    <button
      className="relative h-7 w-12 rounded-full border transition"
      style={{ background: checked ? THEME.colors.accent : "rgba(255,255,255,0.82)", borderColor: checked ? "rgba(151,111,237,0.60)" : THEME.colors.border }}
    >
      <span className={cn("absolute top-1 h-5 w-5 rounded-full bg-white shadow-lg transition", checked ? "left-6" : "left-1")} />
    </button>
  );
}

function Checkbox({ checked = true, label }) {
  return (
    <div className="flex items-center gap-3 text-sm" style={{ color: "rgba(17,17,17,0.76)" }}>
      <div
        className="grid h-5 w-5 place-items-center rounded-md border"
        style={{ background: checked ? THEME.colors.accent : "rgba(255,255,255,0.72)", borderColor: checked ? THEME.colors.accent : THEME.colors.borderStrong }}
      >
        {checked && <Icon name="check" className="h-3.5 w-3.5 text-white" />}
      </div>
      {label}
    </div>
  );
}

function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 p-4 lg:block">
      <GlassPanel className="min-h-[calc(100vh-2rem)] p-4">
        <div className="flex items-center gap-3 px-2 py-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl" style={{ background: THEME.colors.accent, boxShadow: "0 12px 28px rgba(151,111,237,0.24)", color: "#FFFFFF" }}>
            <Icon name="sparkles" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-base font-semibold" style={{ color: THEME.colors.ink }}>Nova UI</p>
            <p className="text-xs" style={{ color: THEME.colors.subtle }}>Liquid design system</p>
          </div>
        </div>
        <nav className="mt-8 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.label}
              className="flex h-12 w-full items-center gap-3 rounded-2xl px-4 text-sm transition"
              style={{
                background: item.active ? "rgba(151,111,237,0.16)" : "transparent",
                border: item.active ? "1px solid rgba(151,111,237,0.35)" : "1px solid transparent",
                color: item.active ? THEME.colors.ink : "rgba(17,17,17,0.68)",
              }}
            >
              <Icon name={item.icon} className="h-4 w-4" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="mt-8 rounded-3xl border p-4" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
          <div className="mb-3 flex items-center justify-between">
            <Badge>Pro</Badge>
            <Icon name="arrowUpRight" className="h-4 w-4" style={{ color: THEME.colors.subtle }} />
          </div>
          <p className="text-sm font-medium" style={{ color: THEME.colors.ink }}>Glass workspace</p>
          <p className="mt-1 text-xs leading-5" style={{ color: THEME.colors.subtle }}>Use blur, depth and restrained purple accents for premium interfaces.</p>
          <Button className="mt-4 w-full" size="sm">Upgrade</Button>
        </div>
      </GlassPanel>
    </aside>
  );
}

function Topbar() {
  return (
    <div className="sticky top-0 z-30 border-b px-4 py-4 backdrop-blur-2xl lg:px-8" style={{ background: "rgba(255,255,255,0.62)", borderColor: THEME.colors.border }}>
      <div className="flex items-center gap-3">
        <Button variant="secondary" size="sm" className="lg:hidden" icon="menu">Menu</Button>
        <div className="relative flex-1">
          <Icon name="search" className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: THEME.colors.accentText }} />
          <input
            className="h-12 w-full rounded-2xl border pl-11 pr-4 text-sm outline-none backdrop-blur-xl"
            placeholder="Search components, tokens, patterns..."
            style={{ background: "rgba(255,255,255,0.90)", borderColor: THEME.colors.border, color: THEME.colors.ink }}
          />
        </div>
        <Button variant="secondary" size="sm" icon="bell">Alerts</Button>
        <div className="grid h-11 w-11 place-items-center rounded-2xl border" style={{ background: THEME.colors.card, borderColor: THEME.colors.border }}>
          <Icon name="user" className="h-4 w-4" style={{ color: THEME.colors.muted }} />
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, change, icon }) {
  return (
    <GlassPanel className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm" style={{ color: THEME.colors.subtle }}>{title}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight" style={{ color: THEME.colors.ink }}>{value}</p>
          <p className="mt-2 text-sm" style={{ color: THEME.colors.accentText }}>{change}</p>
        </div>
        <div className="grid h-12 w-12 place-items-center rounded-2xl border" style={{ background: "rgba(151,111,237,0.15)", borderColor: "rgba(151,111,237,0.30)", color: THEME.colors.accentText }}>
          <Icon name={icon} className="h-5 w-5" />
        </div>
      </div>
    </GlassPanel>
  );
}

function ComponentCard({ title, children, className = "" }) {
  return (
    <GlassPanel className={cn("p-5", className)}>
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-base font-semibold" style={{ color: THEME.colors.ink }}>{title}</h3>
        <Icon name="more" className="h-5 w-5" style={{ color: THEME.colors.subtle }} />
      </div>
      {children}
    </GlassPanel>
  );
}

function Tabs() {
  const tabs = ["Overview", "Components", "Tokens", "Docs"];
  return (
    <div className="flex rounded-2xl border p-1" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
      {tabs.map((tab, index) => (
        <button
          key={tab}
          className="flex-1 rounded-xl px-3 py-2 text-sm transition"
          style={{ background: index === 0 ? "rgba(151,111,237,0.13)" : "transparent", color: index === 0 ? THEME.colors.accentText : THEME.colors.muted }}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

function DataTable() {
  const rows = [
    ["Glass Button", "Primitive", "Stable", "98%"],
    ["Input Field", "Form", "Review", "91%"],
    ["Sidebar", "Navigation", "Stable", "96%"],
    ["Data Table", "Display", "Draft", "84%"],
  ];

  return (
    <div className="overflow-hidden rounded-3xl border" style={{ borderColor: THEME.colors.border }}>
      <table className="w-full text-left text-sm">
        <thead style={{ background: "rgba(255,255,255,0.86)", color: THEME.colors.muted }}>
          <tr>
            <th className="px-4 py-3 font-medium">Component</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Score</th>
          </tr>
        </thead>
        <tbody style={{ color: "rgba(17,17,17,0.82)" }}>
          {rows.map((row) => (
            <tr key={row[0]} style={{ borderTop: "1px solid rgba(17,17,17,0.08)" }}>
              <td className="px-4 py-3 font-medium" style={{ color: "rgba(17,17,17,0.90)" }}>{row[0]}</td>
              <td className="px-4 py-3">{row[1]}</td>
              <td className="px-4 py-3"><Badge tone={row[2] === "Stable" ? "green" : row[2] === "Review" ? "orange" : "neutral"}>{row[2]}</Badge></td>
              <td className="px-4 py-3">{row[3]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ColorToken({ color, name }) {
  return (
    <div className="rounded-3xl border p-3" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
      <div className="h-20 rounded-2xl border" style={{ background: color, borderColor: THEME.colors.border }} />
      <p className="mt-3 text-sm font-medium" style={{ color: THEME.colors.ink }}>{name}</p>
      <p className="text-xs" style={{ color: THEME.colors.subtle }}>{color}</p>
    </div>
  );
}

export default function LiquidGlassDesignSystem() {
  const [showToast, setShowToast] = useState(true);

  useEffect(() => {
    runDesignSystemTests();
  }, []);

  return (
    <div className="min-h-screen overflow-hidden font-sans" style={{ background: THEME.colors.base, color: THEME.colors.ink }}>
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full blur-3xl" style={{ background: "rgba(151,111,237,0.26)" }} />
        <div className="absolute right-0 top-1/4 h-[32rem] w-[32rem] rounded-full blur-3xl" style={{ background: "rgba(151,111,237,0.14)" }} />
        <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full blur-3xl" style={{ background: "rgba(17,17,17,0.04)" }} />
        <div className="absolute inset-0 opacity-45" style={{ backgroundImage: "radial-gradient(circle at 1px 1px, rgba(17,17,17,0.045) 1px, transparent 0)", backgroundSize: "28px 28px" }} />
      </div>

      <div className="relative flex">
        <Sidebar />
        <main className="min-w-0 flex-1">
          <Topbar />

          <section className="px-4 py-8 lg:px-8">
            <div>
              <div className="mb-8 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
                <div>
                  <Badge tone="orange">Liquid Glass · White / Purple</Badge>
                  <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-[-0.04em] md:text-6xl" style={{ color: THEME.colors.ink }}>
                    A premium component system with depth, blur and high-contrast purple energy.
                  </h1>
                  <p className="mt-5 max-w-2xl text-base leading-7" style={{ color: THEME.colors.muted }}>
                    Components inspired by shadcn primitives, redesigned with translucent panels, soft borders, white surfaces and controlled liquid highlights.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button icon="plus">New component</Button>
                  <Button variant="secondary" icon="command">Command menu</Button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <StatCard title="Components" value="42" change="+12 this sprint" icon="layers" />
                <StatCard title="Token coverage" value="96%" change="Color, radius, blur" icon="sparkles" />
                <StatCard title="Accessibility" value="AA" change="Contrast-first system" icon="shield" />
                <StatCard title="Adoption" value="8.7k" change="Reusable instances" icon="chart" />
              </div>

              <div className="mt-8 grid gap-5 xl:grid-cols-3">
                <ComponentCard title="Core Actions" className="xl:col-span-1">
                  <div className="flex flex-wrap gap-3">
                    <Button>Primary</Button>
                    <Button variant="secondary">Secondary</Button>
                    <Button variant="outline">Outline</Button>
                    <Button variant="ghost">Ghost</Button>
                    <Button variant="dark">Dark</Button>
                    <Button size="sm" icon="plus">Small</Button>
                    <Button size="lg" icon="arrowUpRight">Large CTA</Button>
                  </div>
                </ComponentCard>

                <ComponentCard title="Forms" className="xl:col-span-2">
                  <div className="grid gap-4 md:grid-cols-2">
                    <Input placeholder="Email address" icon="mail" value="jailson@nova.io" />
                    <Input placeholder="Password" icon="lock" type="password" value="liquidglass" />
                    <Input placeholder="Search product" icon="search" />
                    <Input placeholder="Due date" icon="calendar" error="Use a future date." />
                    <SelectBox label="Workspace" value="Design System" options={["Design System", "Admin Panel", "Customer Portal", "Mobile App"]} />
                    <div className="space-y-4 rounded-3xl border p-4" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium" style={{ color: THEME.colors.ink }}>Notifications</p>
                          <p className="text-xs" style={{ color: THEME.colors.subtle }}>Enable system alerts</p>
                        </div>
                        <Toggle />
                      </div>
                      <Checkbox label="Remember preferences" />
                      <Checkbox checked={false} label="Share anonymous usage" />
                    </div>
                  </div>
                </ComponentCard>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-3">
                <ComponentCard title="Tokens">
                  <div className="grid grid-cols-2 gap-3">
                    <ColorToken color={THEME.colors.base} name="Base White" />
                    <ColorToken color={THEME.colors.accent} name="Signal Purple" />
                    <ColorToken color={THEME.colors.card} name="Glass Fill" />
                    <ColorToken color={THEME.colors.border} name="Glass Stroke" />
                  </div>
                  <div className="mt-5 rounded-3xl border p-4" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
                    <p className="text-sm font-semibold" style={{ color: THEME.colors.ink }}>Radii</p>
                    <div className="mt-3 grid grid-cols-4 gap-2">
                      {["12", "16", "24", "32"].map((r) => (
                        <div key={r} className="grid h-14 place-items-center border text-xs" style={{ borderRadius: `${r}px`, borderColor: "rgba(151,111,237,0.30)", background: "rgba(151,111,237,0.12)", color: THEME.colors.muted }}>{r}px</div>
                      ))}
                    </div>
                  </div>
                </ComponentCard>

                <ComponentCard title="Navigation + Filters" className="xl:col-span-2">
                  <Tabs />
                  <div className="mt-5 flex flex-wrap items-center gap-3 rounded-3xl border p-4" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
                    <Button variant="secondary" icon="filter">Filter</Button>
                    <Badge>In review</Badge>
                    <Badge tone="green">Published</Badge>
                    <Badge tone="blue">Experimental</Badge>
                    <Badge tone="neutral">Deprecated</Badge>
                    <div className="ml-auto flex items-center gap-2 rounded-2xl border px-3 py-2 text-sm" style={{ background: "rgba(255,255,255,0.88)", borderColor: THEME.colors.border, color: THEME.colors.muted }}>
                      <Icon name="upload" className="h-4 w-4" /> Import tokens
                    </div>
                  </div>
                  <div className="mt-5 grid gap-4 md:grid-cols-3">
                    {[
                      ["Glass Card", "layers"],
                      ["Command Bar", "command"],
                      ["Payment Form", "creditCard"],
                    ].map(([title, icon]) => (
                      <div key={title} className="rounded-3xl border p-4" style={{ background: THEME.colors.cardStrong, borderColor: THEME.colors.border }}>
                        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl" style={{ background: "rgba(151,111,237,0.15)", color: THEME.colors.accentText }}>
                          <Icon name={icon} className="h-5 w-5" />
                        </div>
                        <p className="text-sm font-semibold" style={{ color: THEME.colors.ink }}>{title}</p>
                        <p className="mt-1 text-xs leading-5" style={{ color: THEME.colors.muted }}>Reusable primitive with variants, focus rings, density and glass states.</p>
                      </div>
                    ))}
                  </div>
                </ComponentCard>
              </div>

              <div className="mt-5 grid gap-5 xl:grid-cols-5">
                <ComponentCard title="Data Table" className="xl:col-span-3">
                  <DataTable />
                </ComponentCard>

                <ComponentCard title="Dialog / Toast" className="xl:col-span-2">
                  <div className="rounded-3xl border p-5 shadow-2xl backdrop-blur-2xl" style={{ background: "rgba(255,255,255,0.76)", borderColor: THEME.colors.border }}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="grid h-11 w-11 place-items-center rounded-2xl" style={{ background: "rgba(151,111,237,0.18)", color: THEME.colors.accentText }}>
                        <Icon name="sparkles" className="h-5 w-5" />
                      </div>
                      <button className="grid h-8 w-8 place-items-center rounded-xl" style={{ background: "rgba(255,255,255,0.88)", color: THEME.colors.muted }}>
                        <Icon name="x" className="h-4 w-4" />
                      </button>
                    </div>
                    <h3 className="mt-5 text-xl font-semibold tracking-tight" style={{ color: THEME.colors.ink }}>Publish component?</h3>
                    <p className="mt-2 text-sm leading-6" style={{ color: THEME.colors.muted }}>This action promotes the primitive to the shared library and locks the current API contract.</p>
                    <div className="mt-5 flex gap-3">
                      <Button>Publish</Button>
                      <Button variant="secondary">Cancel</Button>
                    </div>
                  </div>

                  {showToast && (
                    <div className="mt-4 flex items-start gap-3 rounded-3xl border p-4 backdrop-blur-xl" style={{ background: "rgba(151,111,237,0.14)", borderColor: "rgba(151,111,237,0.30)" }}>
                      <div className="grid h-8 w-8 place-items-center rounded-xl text-white" style={{ background: THEME.colors.accent }}>
                        <Icon name="check" className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium" style={{ color: THEME.colors.ink }}>Tokens synced</p>
                        <p className="text-xs leading-5" style={{ color: THEME.colors.muted }}>Theme variables are ready for production.</p>
                      </div>
                      <button onClick={() => setShowToast(false)} style={{ color: THEME.colors.muted }}>
                        <Icon name="x" className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </ComponentCard>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
