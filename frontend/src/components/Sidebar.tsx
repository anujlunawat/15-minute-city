interface SidebarProps {
  totalNodes: number;
}

export default function Sidebar({ totalNodes }: SidebarProps) {
  return (
    <div className="sidebar">
      <h2>15-Min City Auditor</h2>
      <p>Total Nodes: {totalNodes}</p>
      <p>Green = ≤ 15 min to grocery</p>
      <p>Red = `$gt` 15 min</p>
    </div>
  );
}