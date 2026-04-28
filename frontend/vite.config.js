import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const isPharmacist = mode === 'pharmacist';
  
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: "0.0.0.0",
      port: 5173,
    },
    preview: {
      host: "0.0.0.0",
      port: 80,
    },
    build: {
      outDir: isPharmacist ? "dist-pharmacist" : "dist",
      sourcemap: false,
      rollupOptions: {
        input: isPharmacist ? "src/pharmacist-main.jsx" : undefined,
        output: {
          manualChunks: {
            "react-vendor": ["react", "react-dom"],
          },
        },
      },
    },
    // Убедимся что base правильный
    base: "/",
  };
});
