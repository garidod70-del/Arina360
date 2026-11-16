import { useEffect, useState } from 'react';

const modules = [
  ['Шүүгчийн үйлчилгээ', 'Шүүгчийн хүсэлт, зэрэглэл, хуваарь', '01'],
  ['Тэмцээн', 'Бүртгэл, сугалаа, хүснэгт, оноо', '02'],
  ['Клуб, секц', 'Клубын мэдээлэл, дасгалжуулагч, гишүүд', '03'],
  ['Заал түрээс', 'Байршил, цагийн хуваарь, захиалга', '04'],
  ['Сургалт', 'Дасгалжуулагч, шүүгчийн сургалт', '05'],
  ['Фитнес', 'Эрхийн бичиг, QR баталгаажуулалт', '06'],
  ['Спорт бараа', 'Бараа, үйлчилгээ, захиалга', '07'],
];

export default function App() {
  const [apiStatus, setApiStatus] = useState('Шалгаагүй');
  const [apiModules, setApiModules] = useState([]);
  const [lastChecked, setLastChecked] = useState('');

  async function checkApi() {
    const base = import.meta.env.VITE_API_URL || 'http://localhost:5000';
    try {
      const [health, moduleResponse] = await Promise.all([
        fetch(base + '/api/health'),
        fetch(base + '/api/modules')
      ]);
      if (!health.ok || !moduleResponse.ok) throw new Error('API response error');
      const data = await health.json();
      setApiModules(await moduleResponse.json());
      setApiStatus(data.status === 'healthy' ? 'Холбогдсон' : 'Тодорхойгүй');
    } catch {
      setApiStatus('Холбогдоогүй');
      setApiModules([]);
    }
    setLastChecked(new Date().toLocaleTimeString('mn-MN'));
  }

  useEffect(() => { checkApi(); }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">A</span><div><b>ARENA 360</b><small>SPORTS PLATFORM</small></div></div>
        <div className="nav-label">ҮНДСЭН ЦЭС</div>
        <a className="nav active" href="#overview">▦　 Ерөнхий самбар</a>
        <a className="nav" href="#modules">◈　 Үйлчилгээний модулиуд</a>
        <a className="nav" href="#system">⚙　 Системийн төлөв</a>
        <div className="sidebar-bottom"><span className="dot"></span> Platform foundation v0.1</div>
      </aside>
      <main className="main" id="overview">
        <header className="topbar"><div><span className="eyebrow">УДИРДЛАГЫН СИСТЕМ</span><h1>Ерөнхий самбар</h1></div><div className="admin-chip"><span className="avatar">A</span><span>Админ</span></div></header>
        <section className="welcome"><div><span className="eyebrow light">НЭГДСЭН СПОРТЫН ПЛАТФОРМ</span><h2>Спортын үйлчилгээг<br/>нэг дороос.</h2><p>ARENA 360 системийн удирдлагын эхний хувилбар.</p></div><div className="welcome-orbit">360°</div></section>
        <section className="stats">
          <article className="stat"><span>Нийт үйлчилгээний модуль</span><strong>07</strong><small>Төлөвлөсөн үндсэн чиглэл</small></article>
          <article className="stat"><span>API холболт</span><strong className={apiStatus === 'Холбогдсон' ? 'ok' : 'pending'}>{apiStatus}</strong><small>{lastChecked ? 'Сүүлд шалгасан: ' + lastChecked : 'API шалгалт'}</small></article>
          <article className="stat"><span>Платформын хувилбар</span><strong>0.1.0</strong><small>Хөгжүүлэлтийн суурь</small></article>
        </section>
        <section className="section" id="modules"><div className="section-heading"><div><span className="eyebrow">PLATFORM SERVICES</span><h3>Үйлчилгээний модулиуд</h3></div><span className="count">7 МОДУЛЬ</span></div>
          <div className="module-grid">{modules.map(([name, desc, number]) => <article className="module" key={number}><span className="module-number">{number}</span><h4>{name}</h4><p>{desc}</p><span className="module-link">Хөгжүүлэлтийн жагсаалт <b>↗</b></span></article>)}</div>
        </section>
        <section className="system-panel" id="system"><div><span className="eyebrow">SYSTEM CONNECTION</span><h3>Backend холболт</h3><p>API серверийг асаасны дараа холболтоо шалгана.</p></div><button onClick={checkApi}>Холболт шалгах ↻</button></section>
        <footer>© 2026 ARENA 360 · Монголын спортын нэгдсэн платформ</footer>
      </main>
    </div>
  );
}
