import { createHashRouter, RouterProvider } from "react-router-dom";
import { Atmosphere } from "./field/Atmosphere";
import { Assist } from "./screens/Assist";
import { Review } from "./screens/Review";

const router = createHashRouter([
  { path: "/", element: <Review /> },
  { path: "/doc/:id", element: <Review /> },
  { path: "/asistente", element: <Assist /> },
]);

export default function App() {
  return (
    <>
      <Atmosphere />
      <RouterProvider router={router} />
    </>
  );
}
