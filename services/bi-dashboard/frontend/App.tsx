import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PrivateRoute from './components/PrivateRoute';
import HomePage from './pages/HomePage';
import PipelinesPage from './pages/PipelinesPage';
import QualityPage from './pages/QualityPage';
import LineagePage from './pages/LineagePage';
import CatalogPage from './pages/CatalogPage';
import ReportsPage from './pages/ReportsPage';
import AdminPage from './pages/AdminPage';
import UsersPage from './pages/UsersPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/" element={<PrivateRoute><HomePage /></PrivateRoute>} />
        <Route path="/pipelines" element={<PrivateRoute><PipelinesPage /></PrivateRoute>} />
        <Route path="/quality" element={<PrivateRoute><QualityPage /></PrivateRoute>} />
        <Route path="/lineage" element={<PrivateRoute><LineagePage /></PrivateRoute>} />
        <Route path="/catalog" element={<PrivateRoute><CatalogPage /></PrivateRoute>} />
        <Route path="/reports" element={<PrivateRoute><ReportsPage /></PrivateRoute>} />
        <Route path="/admin" element={<PrivateRoute><AdminPage /></PrivateRoute>} />
        <Route path="/admin/users" element={<PrivateRoute><UsersPage /></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
