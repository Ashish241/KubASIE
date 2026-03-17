import ScalingPanel from '../components/ScalingPanel';

export default function Scaling() {
  return (
    <>
      <div className="page-header">
        <h2>Scaling Controls</h2>
        <p>Horizontal Pod Autoscaler status, manual override, and event history</p>
      </div>
      <ScalingPanel />
    </>
  );
}
