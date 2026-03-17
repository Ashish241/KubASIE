import SlaGauge from '../components/SlaGauge';

export default function Sla() {
  return (
    <>
      <div className="page-header">
        <h2>SLA Monitoring</h2>
        <p>Service Level Agreement compliance tracking and latency trends</p>
      </div>
      <SlaGauge />
    </>
  );
}
