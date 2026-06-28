export interface NavItem {
  href: string;
  label: string;
  icon: string; // inline SVG path data
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    href: "/data",
    label: "Data",
    description: "Upload & validate inputs",
    icon: "M7 16a4 4 0 01-.88-7.9A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 13l3-3m0 0l3 3m-3-3v9",
  },
  {
    href: "/overview",
    label: "Overview",
    description: "Twin snapshot & KPIs",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  },
  {
    href: "/forecasting",
    label: "Forecasting",
    description: "Demand methods & accuracy",
    icon: "M3 3v18h18M7 14l4-4 3 3 5-6",
  },
  {
    href: "/suppliers",
    label: "Suppliers",
    description: "Collection-center availability",
    icon: "M3 7h18M3 12h18M3 17h18",
  },
  {
    href: "/transportation",
    label: "Transportation",
    description: "Route optimisation",
    icon: "M9 17a2 2 0 11-4 0 2 2 0 014 0zm10 0a2 2 0 11-4 0 2 2 0 014 0zM5 17H3V5h11v12m0 0h5v-4l-3-4h-2v8",
  },
  {
    href: "/warehouse",
    label: "Warehouse",
    description: "Inventory policy",
    icon: "M3 9l9-6 9 6v11a1 1 0 01-1 1H4a1 1 0 01-1-1V9z M9 21V12h6v9",
  },
  {
    href: "/scenario",
    label: "Scenario",
    description: "Normal vs Disruption",
    icon: "M8 7h12m0 0l-4-4m4 4l-4 4M16 17H4m0 0l4 4m-4-4l4-4",
  },
];
