import { useEffect, useState } from "react";
import MapView from "../components/MapView";
// import Sidebar from "../components/Sidebar";
import { fetchNodes } from "../api/nodes";
import { type NodeData } from "../types/Node";

function MainPage() {
  const [nodes, setNodes] = useState<NodeData[]>([]);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchNodes();
        setNodes(data);
      } catch (error) {
        console.error(error);
      }
    }
    loadData();
  }, []);

  return (
    <div className="app-container">
      {/* <Sidebar totalNodes={nodes.length} /> */}
      <MapView nodes={nodes} />
    </div>
  );
}

export default MainPage;
