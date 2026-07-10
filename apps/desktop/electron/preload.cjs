const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('cyberfoxDesktop', {
  getConnection: profile => ipcRenderer.invoke('cyberfox:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('cyberfox:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('cyberfox:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('cyberfox:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('cyberfox:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('cyberfox:window:openNewSession'),
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('cyberfox:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('cyberfox:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('cyberfox:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('cyberfox:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('cyberfox:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('cyberfox:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('cyberfox:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('cyberfox:pet-overlay:state', listener)
      return () => ipcRenderer.removeListener('cyberfox:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('cyberfox:pet-overlay:control', listener)
      return () => ipcRenderer.removeListener('cyberfox:pet-overlay:control', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('cyberfox:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('cyberfox:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('cyberfox:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('cyberfox:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('cyberfox:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('cyberfox:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('cyberfox:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('cyberfox:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('cyberfox:profile:get'),
    set: name => ipcRenderer.invoke('cyberfox:profile:set', name)
  },
  api: request => ipcRenderer.invoke('cyberfox:api', request),
  notify: payload => ipcRenderer.invoke('cyberfox:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('cyberfox:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('cyberfox:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('cyberfox:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('cyberfox:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('cyberfox:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('cyberfox:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('cyberfox:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('cyberfox:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('cyberfox:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('cyberfox:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('cyberfox:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('cyberfox:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('cyberfox:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('cyberfox:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('cyberfox:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('cyberfox:openExternal', url),
  openPreviewInBrowser: url => ipcRenderer.invoke('cyberfox:openPreviewInBrowser', url),
  fetchLinkTitle: url => ipcRenderer.invoke('cyberfox:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('cyberfox:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('cyberfox:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('cyberfox:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('cyberfox:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('cyberfox:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('cyberfox:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('cyberfox:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('cyberfox:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('cyberfox:fs:reveal', targetPath),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('cyberfox:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('cyberfox:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('cyberfox:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('cyberfox:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('cyberfox:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('cyberfox:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('cyberfox:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('cyberfox:git:branchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('cyberfox:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('cyberfox:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('cyberfox:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('cyberfox:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('cyberfox:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('cyberfox:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('cyberfox:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('cyberfox:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('cyberfox:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('cyberfox:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('cyberfox:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('cyberfox:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('cyberfox:git:review:shipInfo', repoPath),
      createPr: repoPath => ipcRenderer.invoke('cyberfox:git:review:createPr', repoPath)
    }
  },
  terminal: {
    dispose: id => ipcRenderer.invoke('cyberfox:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('cyberfox:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('cyberfox:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('cyberfox:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `cyberfox:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `cyberfox:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('cyberfox:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('cyberfox:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('cyberfox:open-updates', listener)
    return () => ipcRenderer.removeListener('cyberfox:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:deep-link', listener)
    return () => ipcRenderer.removeListener('cyberfox:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('cyberfox:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:window-state-changed', listener)
    return () => ipcRenderer.removeListener('cyberfox:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('cyberfox:focus-session', listener)
    return () => ipcRenderer.removeListener('cyberfox:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:notification-action', listener)
    return () => ipcRenderer.removeListener('cyberfox:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('cyberfox:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:backend-exit', listener)
    return () => ipcRenderer.removeListener('cyberfox:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('cyberfox:power-resume', listener)
    return () => ipcRenderer.removeListener('cyberfox:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:boot-progress', listener)
    return () => ipcRenderer.removeListener('cyberfox:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.cjs (apps/desktop/electron/bootstrap-runner.cjs).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('cyberfox:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('cyberfox:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('cyberfox:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('cyberfox:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('cyberfox:bootstrap:event', listener)
    return () => ipcRenderer.removeListener('cyberfox:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('cyberfox:version'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('cyberfox:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('cyberfox:uninstall:summary'),
    run: mode => ipcRenderer.invoke('cyberfox:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('cyberfox:updates:check'),
    apply: opts => ipcRenderer.invoke('cyberfox:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('cyberfox:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('cyberfox:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('cyberfox:updates:progress', listener)
      return () => ipcRenderer.removeListener('cyberfox:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('cyberfox:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('cyberfox:vscode-theme:search', query)
  }
})
