import React from 'react'
import ReactDOM from 'react-dom/client'
import { App, PaxPage, PerfPage } from './App.tsx'
import { NextUIProvider } from "@nextui-org/react";
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './output.css'

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      {
        path: "/perf",
        element: <PerfPage />
      },
      {
        path: "/pax",
        element: <PaxPage />
      }
    ]
  }
])


ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <NextUIProvider>
      <RouterProvider router={router}></RouterProvider>
    </NextUIProvider>
  </React.StrictMode>,
)
