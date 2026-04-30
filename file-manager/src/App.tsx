import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navigation from "./components/Navbar";
import FileManager from "./pages/FileManager";

function App() {
  return (
    <Router>
      <Navigation />
      <Routes>
        <Route path="/" element={<FileManager />} />
      </Routes>
    </Router>
  );
}

export default App;