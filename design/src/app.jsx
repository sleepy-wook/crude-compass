function App() {
  const [page, setPage] = React.useState("discovery");

  React.useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      if (e.key === "1") setPage("discovery");
      if (e.key === "2") setPage("mission");
      if (e.key === "3") setPage("whatif");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar page={page} setPage={setPage}/>
      <main style={{ flex: 1, minWidth: 0 }} key={page}>
        <div className="stagger">
          {page === "discovery" && <PageDiscovery/>}
          {page === "mission" && <PageMission/>}
          {page === "whatif" && <PageWhatIf/>}
        </div>
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
