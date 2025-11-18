// /opt/VCPToolBox/ecosystem.config.js
module.exports = {
  apps: [{
    name: 'vcp',
    script: './start_wrapper.sh',
    interpreter: '/bin/bash',   // 明确用 bash 执行脚本更稳
    time: true,
    max_restarts: 10,
    restart_delay: 3000
  }]
}
