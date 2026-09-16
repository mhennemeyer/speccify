export function installUpdateFixture(responses, emit) {
  const control = window.__SPECCIFY_MOCK__;
  const state = control.update = {
    current_version: '0.8.0', supported: true, reason: null,
    preferences: JSON.parse(localStorage.getItem('test.update-preferences') ?? '{"automatic":true,"interval_hours":24}'),
    phase: 'idle', version: null, notes: null, downloaded: 0, total: null, last_checked: null, error: null,
  };
  control.updateInstalls = 0;
  responses.update_snapshot = () => state;
  responses.update_preferences = ({preferences}) => {
    state.preferences = preferences;
    localStorage.setItem('test.update-preferences', JSON.stringify(preferences));
  };
  responses.update_check = () => {
    state.last_checked = Math.floor(Date.now()/1000);
    state.error = control.updateOffline ? 'Update server offline' : null;
    state.phase = control.updateOffline ? 'error' : 'available';
    if (!control.updateOffline) { state.version = '0.9.0'; state.notes = '# Improvements\n\nSigned app updates.'; }
  };
  let finish;
  responses.update_download = () => {
    state.phase = 'downloading'; state.error = null; state.downloaded = 250000; state.total = 1000000;
    return new Promise(resolve => { finish = resolve; });
  };
  responses.update_cancel = () => { state.phase = 'available'; state.downloaded = 0; finish?.(); };
  control.finishUpdateDownload = (valid=true) => {
    state.phase = valid ? 'ready' : 'error'; state.error = valid ? null : 'Invalid signature';
    finish?.();
  };
  responses.update_guard_reply = ({token, blockers}) => { control.updateReport = {token, blockers}; };
  responses.update_install = async () => {
    state.phase = 'preparing'; state.error = null; control.updateReport = null;
    const token = crypto.randomUUID();
    emit('update-guard', token);
    for (let attempt=0;attempt<50 && !control.updateReport;attempt++) await new Promise(resolve=>setTimeout(resolve,10));
    const blockers = control.updateReport?.blockers ?? ['Window did not respond'];
    if (control.updateProcessRunning) blockers.push('Terminals oder Aktionen laufen noch.');
    emit('update-guard-release', token);
    if (blockers.length) {
      state.phase = 'ready'; state.error = blockers.join('\n'); throw Error(state.error);
    }
    control.updateInstalls++;
    state.phase = 'current'; state.version = null;
  };
}
