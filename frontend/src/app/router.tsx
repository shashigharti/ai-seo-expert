import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { AboutPage } from "../pages/AboutPage";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/workflows/:workflowId", element: <DashboardPage /> },
      { path: "/about", element: <AboutPage /> },
    ],
  },
]);
