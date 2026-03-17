import CostChart from '../components/CostChart';

export default function Cost() {
  return (
    <>
      <div className="page-header">
        <h2>Cost Analysis</h2>
        <p>Infrastructure savings compared to running maximum replicas</p>
      </div>
      <CostChart />
    </>
  );
}
