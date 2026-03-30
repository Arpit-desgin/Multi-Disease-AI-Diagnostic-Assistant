import React, { createContext, useContext, useState } from "react";
import type { DiagnosisContext } from "@/lib/api";

type DiagnosisContextState = {
  activeDiagnosis: DiagnosisContext | null;
  setActiveDiagnosis: (d: DiagnosisContext | null) => void;
};

const DiagnosisCtx = createContext<DiagnosisContextState>({
  activeDiagnosis: null,
  setActiveDiagnosis: () => {},
});

export const DiagnosisProvider = ({ children }: { children: React.ReactNode }) => {
  const [activeDiagnosis, setActiveDiagnosis] = useState<DiagnosisContext | null>(null);
  return (
    <DiagnosisCtx.Provider value={{ activeDiagnosis, setActiveDiagnosis }}>
      {children}
    </DiagnosisCtx.Provider>
  );
};

export const useDiagnosisContext = () => useContext(DiagnosisCtx);
