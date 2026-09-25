import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { PlatformProvider } from './context/PlatformContext';
import { RealtimeProvider } from './context/RealtimeContext';

import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import VerifyAccountPage from './pages/VerifyAccountPage';
import VerificationPendingPage from './pages/VerificationPendingPage';
import UnauthorizedPage from './pages/UnauthorizedPage';
import NotificationsPage from './pages/NotificationsPage';
import SettingsPage from './pages/SettingsPage';
import SearchPage from './pages/SearchPage';

// Dashboards
import CandidateDashboard from './pages/dashboards/CandidateDashboard';
import EmployerDashboard from './pages/dashboards/EmployerDashboard';
import InstituteDashboard from './pages/dashboards/InstituteDashboard';
import GovernmentDashboard from './pages/dashboards/GovernmentDashboard';
import AdminDashboard from './pages/dashboards/AdminDashboard';

// Auth Guards & Redirects
import ProtectedRoute from './components/auth/ProtectedRoute';
import DashboardRedirect from './components/auth/DashboardRedirect';

// Public Profiles
import PublicProfilePage from './pages/profile/PublicProfilePage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <PlatformProvider>
        <RealtimeProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            {/* ============================================================ */}
            {/* Public & Authentication */}
            {/* ============================================================ */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/welcome" element={<Navigate to="/" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/verify-account" element={<VerifyAccountPage />} />
            <Route path="/verification-pending" element={<VerificationPendingPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />
            <Route path="/search" element={<SearchPage />} />

            {/* General User Routes */}
            <Route
              path="/notifications"
              element={
                <ProtectedRoute>
                  <NotificationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />

            {/* Smart Dashboard Redirection based on role */}
            <Route path="/dashboard" element={<DashboardRedirect />} />

            {/* ============================================================ */}
            {/* Candidate Protected Canonical Routes & Subroutes */}
            {/* ============================================================ */}
            <Route
              path="/candidate"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="overview" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/skills"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="skills" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/credentials"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="credentials" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/jobs"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="jobs" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/applications"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="applications" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/assessments"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="assessments" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/following"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="following" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/resume"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="resume" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/edit-profile"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="profile" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/profile-management"
              element={
                <ProtectedRoute allowedRoles={['CANDIDATE']}>
                  <CandidateDashboard section="profile" />
                </ProtectedRoute>
              }
            />

            {/* ============================================================ */}
            {/* Employer Protected Canonical Routes & Subroutes */}
            {/* ============================================================ */}
            <Route
              path="/employer"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="overview" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/jobs"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="jobs" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/jobs/create"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="jobs_create" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/jobs/:jobId"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="job_detail" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/applications"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="applications" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/assessments"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="assessments" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/assessments/create"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="assessments_create" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/documents"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="documents" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/profile"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="profile" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employer/following"
              element={
                <ProtectedRoute allowedRoles={['EMPLOYER']}>
                  <EmployerDashboard section="following" />
                </ProtectedRoute>
              }
            />

            {/* ============================================================ */}
            {/* Institution Protected Canonical Routes & Subroutes */}
            {/* ============================================================ */}
            <Route
              path="/institution"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="overview" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/courses"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="courses" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/courses/create"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="courses_create" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/courses/:courseId"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="course_detail" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/skills"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="skills" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/placements"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="placements" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/documents"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="documents" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/profile"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="profile" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/faculty"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="faculty" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/institution/following"
              element={
                <ProtectedRoute allowedRoles={['TRAINING_INSTITUTE']}>
                  <InstituteDashboard section="following" />
                </ProtectedRoute>
              }
            />

            {/* ============================================================ */}
            {/* Government Protected Canonical Routes & Subroutes */}
            {/* ============================================================ */}
            <Route
              path="/government"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="overview" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/drill-down"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="drilldown" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/verifications"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT', 'SUPER_ADMIN']}>
                  <GovernmentDashboard section="verifications" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/documents"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT', 'SUPER_ADMIN']}>
                  <GovernmentDashboard section="documents" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/trends"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="trends" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/demand"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="demand" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/districts"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="districts" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/organizations"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="organizations" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/courses"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="courses" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/following"
              element={
                <ProtectedRoute allowedRoles={['GOVERNMENT']}>
                  <GovernmentDashboard section="following" />
                </ProtectedRoute>
              }
            />

            {/* ============================================================ */}
            {/* Admin Protected Canonical Routes & Subroutes */}
            {/* ============================================================ */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="overview" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/verification"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="verification" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/verification/:applicationId"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="verification_detail" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/verifiers"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="verifiers" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="users" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/platform-control"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="platform_control" />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/audit-logs"
              element={
                <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                  <AdminDashboard section="audit_logs" />
                </ProtectedRoute>
              }
            />

            {/* ============================================================ */}
            {/* Dashboard Route Aliases (redirect to canonical paths) */}
            {/* ============================================================ */}
            <Route path="/candidate/dashboard" element={<Navigate to="/candidate" replace />} />
            <Route path="/employer/dashboard" element={<Navigate to="/employer" replace />} />
            <Route path="/institution/dashboard" element={<Navigate to="/institution" replace />} />
            <Route path="/institute/dashboard" element={<Navigate to="/institution" replace />} />
            <Route path="/institute" element={<Navigate to="/institution" replace />} />
            <Route path="/government/dashboard" element={<Navigate to="/government" replace />} />
            <Route path="/admin/dashboard" element={<Navigate to="/admin" replace />} />

            {/* ============================================================ */}
            {/* Public Profiles (Universal by handle and canonical aliases) */}
            {/* ============================================================ */}
            <Route path="/profile/@:username" element={<PublicProfilePage />} />
            <Route path="/profile/:username" element={<PublicProfilePage />} />
            <Route path="/candidate/profile" element={<PublicProfilePage />} />
            <Route path="/employer/profile" element={<PublicProfilePage />} />
            <Route path="/institution/profile" element={<PublicProfilePage />} />
            <Route path="/institute/profile" element={<PublicProfilePage />} />
            <Route path="/government/profile" element={<PublicProfilePage />} />
            <Route path="/admin/profile" element={<PublicProfilePage />} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        </RealtimeProvider>
      </PlatformProvider>
    </AuthProvider>
  );
};

export default App;
