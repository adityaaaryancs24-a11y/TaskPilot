import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { ErrorBoundary } from "./components/shared/ErrorBoundary";
import { DashboardLayout } from "./components/shared/DashboardLayout";
import { Screen0 } from "./components/screens/Screen0";
import { Dashboard } from "./components/screens/Dashboard";
import { Inbox } from "./components/screens/Inbox";
import { HiddenTasks } from "./components/screens/HiddenTasks";
import { DedupGroups } from "./components/screens/DedupGroups";
import { Planner } from "./components/screens/Planner";
import { Timeline } from "./components/screens/Timeline";
import { Priorities } from "./components/screens/Priorities";
import { Dependencies } from "./components/screens/Dependencies";
import { Reports } from "./components/screens/Reports";
import { Integrations } from "./components/screens/Integrations";
import { Notifications } from "./components/screens/Notifications";
import { Settings } from "./components/screens/Settings";
import { Screen6 } from "./components/screens/Screen6";
import { ChatPage } from "./pages/ChatPage";

function DL({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <DashboardLayout>{children}</DashboardLayout>
    </ErrorBoundary>
  );
}

function Home() {
  return <Navigate to="/dashboard" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Screen0 onStart={() => { window.location.href = "/dashboard"; }} />} />
        <Route path="/dashboard" element={<DL><Dashboard /></DL>} />
        <Route path="/inbox" element={<DL><Inbox /></DL>} />
        <Route path="/hidden" element={<DL><HiddenTasks /></DL>} />
        <Route path="/dedup-groups" element={<DL><DedupGroups /></DL>} />
        <Route path="/planner" element={<DL><Planner /></DL>} />
        <Route path="/timeline" element={<DL><Timeline /></DL>} />
        <Route path="/priorities" element={<DL><Priorities /></DL>} />
        <Route path="/dependencies" element={<DL><Dependencies /></DL>} />
        <Route path="/reports" element={<DL><Reports /></DL>} />
        <Route path="/integrations" element={<DL><Integrations /></DL>} />
        <Route path="/notifications" element={<DL><Notifications /></DL>} />
        <Route path="/settings" element={<DL><Settings /></DL>} />
        <Route path="/chat" element={<DL><ChatPage /></DL>} />
        <Route path="/traces" element={<DL><Screen6 /></DL>} />
        <Route path="*" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}
