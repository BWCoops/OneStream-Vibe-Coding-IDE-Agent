import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { IDELayout } from '@/components/shared/IDELayout';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<IDELayout />} />
      </Routes>
    </BrowserRouter>
  );
}
