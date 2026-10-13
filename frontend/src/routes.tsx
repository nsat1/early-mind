import { Navigate, type RouteObject } from "react-router";
import { AlphabetLayout } from "./pages/alphabet/AlphabetLayout";
import { LettersPage } from "./pages/alphabet/LettersPage";
import { TasksPage } from "./pages/alphabet/TasksPage";
import { HomePage } from "./pages/HomePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ParentPage } from "./pages/ParentPage";
import { paths } from "./paths";

export const routes: RouteObject[] = [
  { path: paths.home, element: <HomePage /> },
  {
    path: paths.alphabet,
    element: <AlphabetLayout />,
    children: [
      { index: true, element: <Navigate to={paths.letters} replace /> },
      { path: paths.letters, element: <LettersPage /> },
      { path: paths.tasks, element: <TasksPage /> },
    ],
  },
  { path: paths.parent, element: <ParentPage /> },
  { path: "*", element: <NotFoundPage /> },
];
