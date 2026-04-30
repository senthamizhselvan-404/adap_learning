import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../App'
import { LayoutDashboard, Map, BookOpen, FileText, Shield, LogOut, Terminal, Youtube } from 'lucide-react'

export default function Navbar() {
  const { user, logout } = useAuth()
  const loc = useLocation()

  const navItems = [
    { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/roadmap',    icon: Map,              label: 'Roadmap' },
    { to: '/skills',     icon: BookOpen,         label: 'Skills' },
    { to: '/ide',        icon: Terminal,         label: 'IDE' },
    { to: '/youtube',    icon: Youtube,          label: 'YouTube' },
    { to: '/curriculum', icon: FileText,         label: 'Curriculum' },
    ...(user?.role === 'admin' ? [{ to: '/admin', icon: Shield, label: 'Admin' }] : []),
  ]

  return (
    <nav className="fixed top-0 inset-x-0 z-50 h-16 bg-slate-900/90 border-b border-white/10 backdrop-blur-md flex items-center px-6 gap-6">
      <Link to="/dashboard" className="font-bold text-brand-500 text-lg tracking-tight mr-4">
        ⬡ EALPS
      </Link>

      <div className="flex items-center gap-1 flex-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <Link
            key={to}
            to={to}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
              ${loc.pathname.startsWith(to)
                ? 'bg-brand-500/20 text-brand-400'
                : 'text-slate-400 hover:text-slate-100 hover:bg-white/5'}`}
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-3 text-sm">
        <span className="text-slate-400">{user?.full_name}</span>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
          user?.role === 'admin' ? 'bg-amber-500/20 text-amber-400' : 'bg-brand-500/20 text-brand-400'
        }`}>{user?.role}</span>
        <button onClick={logout}
          className="flex items-center gap-1.5 text-slate-400 hover:text-red-400 transition-colors">
          <LogOut size={15} />
        </button>
      </div>
    </nav>
  )
}
