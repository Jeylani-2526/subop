import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from '../HomePage';
import PipelinesPage from '../PipelinesPage';
import QualityPage from '../QualityPage';
import LineagePage from '../LineagePage';
import CatalogPage from '../CatalogPage';
import ReportsPage from '../ReportsPage';
import AdminPage from '../AdminPage';
import UsersPage from '../UsersPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/pipelines" element={<PipelinesPage />} />
        <Route path="/quality" element={<QualityPage />} />
        <Route path="/lineage" element={<LineagePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/users" element={<UsersPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}