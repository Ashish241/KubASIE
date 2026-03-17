import SettingsForm from '../components/SettingsForm';

export default function Settings() {
  return (
    <>
      <div className="page-header">
        <h2>Engine Settings</h2>
        <p>Configure scaling policy weights, SLA thresholds, and cooldown periods</p>
      </div>
      <SettingsForm />
    </>
  );
}
