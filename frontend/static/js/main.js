// WebSocket 连接
const socket = io('http://127.0.0.1:5000');
let gameData = {};
let allVoteResults = {}; // 存储所有回合的投票结果，键为 "gameNumber_round" 或 "round"
let allDescriptions = {}; // 存储所有回合的描述记录，键为 "gameNumber_round" 或 "round"
let gameRoundMapping = {}; // 映射：round -> gameNumber（用于单轮游戏或兼容性）
let descriptionRoundMapping = {}; // 映射：round -> gameNumber（用于描述记录）
let voteRoundMapping = {}; // 映射：round -> gameNumber（用于投票记录）

// localStorage 键名
const STORAGE_KEYS = {
    VOTE_RESULTS: 'undercover_vote_results',
    DESCRIPTIONS: 'undercover_descriptions',
    ROUND_MAPPINGS: 'undercover_round_mappings',
    MULTI_ROUND_CONFIG: 'undercover_multi_round_config',
    CURRENT_ROUND_INDEX: 'undercover_current_round_index',
    TOTAL_ROUNDS: 'undercover_total_rounds'
};

// 保存数据到 localStorage
function saveToLocalStorage() {
    try {
        localStorage.setItem(STORAGE_KEYS.VOTE_RESULTS, JSON.stringify(allVoteResults));
        localStorage.setItem(STORAGE_KEYS.DESCRIPTIONS, JSON.stringify(allDescriptions));
        localStorage.setItem(STORAGE_KEYS.ROUND_MAPPINGS, JSON.stringify({
            gameRoundMapping: gameRoundMapping,
            descriptionRoundMapping: descriptionRoundMapping,
            voteRoundMapping: voteRoundMapping
        }));
        if (totalRounds > 0) {
            localStorage.setItem(STORAGE_KEYS.MULTI_ROUND_CONFIG, JSON.stringify(multiRoundConfig));
            localStorage.setItem(STORAGE_KEYS.CURRENT_ROUND_INDEX, currentRoundIndex.toString());
            localStorage.setItem(STORAGE_KEYS.TOTAL_ROUNDS, totalRounds.toString());
        }
    } catch (e) {
        console.error('保存到 localStorage 失败:', e);
    }
}

// 从 localStorage 恢复数据
function loadFromLocalStorage() {
    try {
        // 恢复投票结果
        const savedVoteResults = localStorage.getItem(STORAGE_KEYS.VOTE_RESULTS);
        if (savedVoteResults) {
            allVoteResults = JSON.parse(savedVoteResults);
        }

        // 恢复描述记录
        const savedDescriptions = localStorage.getItem(STORAGE_KEYS.DESCRIPTIONS);
        if (savedDescriptions) {
            allDescriptions = JSON.parse(savedDescriptions);
        }

        // 恢复轮次映射
        const savedMappings = localStorage.getItem(STORAGE_KEYS.ROUND_MAPPINGS);
        if (savedMappings) {
            const mappings = JSON.parse(savedMappings);
            gameRoundMapping = mappings.gameRoundMapping || {};
            descriptionRoundMapping = mappings.descriptionRoundMapping || {};
            voteRoundMapping = mappings.voteRoundMapping || {};
        }

        // 恢复多轮配置
        const savedConfig = localStorage.getItem(STORAGE_KEYS.MULTI_ROUND_CONFIG);
        if (savedConfig) {
            multiRoundConfig = JSON.parse(savedConfig);
            const savedIndex = localStorage.getItem(STORAGE_KEYS.CURRENT_ROUND_INDEX);
            const savedTotalRounds = localStorage.getItem(STORAGE_KEYS.TOTAL_ROUNDS);
            if (savedIndex !== null) {
                currentRoundIndex = parseInt(savedIndex) || 0;
            }
            if (savedTotalRounds !== null) {
                totalRounds = parseInt(savedTotalRounds) || 0;
            } else if (multiRoundConfig) {
                // 兼容旧数据：如果没有保存总轮数，从配置长度推断
                totalRounds = multiRoundConfig.length;
            }
        }
    } catch (e) {
        console.error('从 localStorage 恢复数据失败:', e);
    }
}

// 清除 localStorage 数据
function clearLocalStorage() {
    try {
        localStorage.removeItem(STORAGE_KEYS.VOTE_RESULTS);
        localStorage.removeItem(STORAGE_KEYS.DESCRIPTIONS);
        localStorage.removeItem(STORAGE_KEYS.ROUND_MAPPINGS);
        localStorage.removeItem(STORAGE_KEYS.MULTI_ROUND_CONFIG);
        localStorage.removeItem(STORAGE_KEYS.CURRENT_ROUND_INDEX);
        localStorage.removeItem(STORAGE_KEYS.TOTAL_ROUNDS);
    } catch (e) {
        console.error('清除 localStorage 失败:', e);
    }
}

// 页面加载时恢复数据
loadFromLocalStorage();

// 连接成功
socket.on('connect', function() {
    console.log('WebSocket 已连接');
    showAlert('success', '已连接到服务器');
    updateServerStatus(true);
    // 请求初始状态
    socket.emit('request_status');
    socket.emit('request_timer');
});

// 接收状态更新推送
socket.on('status_update', function(data) {
    updateRealTimeInfo(data);
    updateTimers(data);
});

// 接收倒计时更新推送
socket.on('timer_update', function(data) {
    updateTimers(data);
    updateGameStateDisplay(data);
});

// 接收完整游戏状态推送
socket.on('game_state_update', function(data) {
    console.log('收到游戏状态推送:', data);
    gameData = data;
    updateAllDisplay();
});

// 接收描述列表更新推送（参考投票记录的机制）
socket.on('descriptions_update', function(data) {
    console.log('收到描述列表更新推送:', data);
    
    // 只在事件中存储描述记录，确保使用正确的轮次号
    if (data.round) {
        // 确定当前是第几轮游戏（显示用的轮次号，从1开始）
        const gameNumber = totalRounds > 0 ? (currentRoundIndex + 1) : null;
        
        // 使用组合键存储：gameNumber_round，例如 "1_1", "1_2", "2_1" 等
        // 这样可以区分不同轮次中相同回合号的记录
        const descKey = gameNumber ? `${gameNumber}_${data.round}` : data.round.toString();
        
        // 存储描述记录（完全替换，确保使用最新的数据）
        if (data.descriptions && data.descriptions.length > 0) {
            allDescriptions[descKey] = data.descriptions;
            
            // 保存回合号到轮次的映射（用于兼容性和显示）
            if (gameNumber) {
                descriptionRoundMapping[data.round] = gameNumber;
            }
            
            // 保存到 localStorage
            saveToLocalStorage();
            
            // 更新显示
            updateDescriptions();
        }
    }
});

// 接收投票结果推送
socket.on('vote_result', function(data) {
    console.log('收到投票结果推送:', data);
    showAlert('warning', '投票结果已生成');

    // 存储投票结果，添加轮次信息
    if (data.round) {
        // 确定当前是第几轮游戏（显示用的轮次号，从1开始）
        const gameNumber = totalRounds > 0 ? (currentRoundIndex + 1) : null;
        
        // 添加轮次信息到结果数据
        data.game_number = gameNumber;
        
        // 使用组合键存储：gameNumber_round，例如 "1_1", "1_2", "2_1" 等
        // 这样可以区分不同轮次中相同回合号的记录
        const resultKey = gameNumber ? `${gameNumber}_${data.round}` : data.round.toString();
        allVoteResults[resultKey] = data;
        
        // 保存回合号到轮次的映射（用于兼容性和显示）
        if (gameNumber) {
            gameRoundMapping[data.round] = gameNumber;
            voteRoundMapping[data.round] = gameNumber;
        }
        
        // 保存到 localStorage
        saveToLocalStorage();
    }

    updateVoteRecords();
    updateGameResults();
    
    // 如果游戏结束且有多轮配置，检查是否需要开始下一轮
    if (data.game_ended && totalRounds > 0) {
        checkAndStartNextRound();
    }
});

// 断开连接时的处理
socket.on('disconnect', function() {
    console.log('WebSocket 已断开');
    showAlert('danger', '与服务器断开连接');
    updateServerStatus(false);
});

// 连接错误
socket.on('connect_error', function(error) {
    console.log('连接错误:', error);
    updateServerStatus(false);
});

// 定时获取游戏状态
setInterval(fetchGameState, 3000);

// 初始加载
fetchGameState();

function fetchGameState() {
    fetch('/api/game/state')
        .then(response => response.json())
        .then(resp => {
            if (resp && resp.code === 200) {
                gameData = resp.data || {};
                updateAllDisplay();
            } else {
                console.error('状态刷新失败：', resp ? resp.message : '未知错误');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            updateServerStatus(false);
        });
}

// 跟踪上一次的游戏状态，用于检测新游戏开始
let lastGameStatus = '';
let lastCurrentRound = 0;
let lastGameNumber = null;

function updateAllDisplay() {
    // 获取当前轮次显示号（从1开始）
    const currentRound = gameData.current_round || 0;
    const gameNumber = totalRounds > 0 ? (currentRoundIndex + 1) : null;
    const currentStatus = gameData.status || '';
    
    // 检测新游戏开始：
    // 1. 状态从 game_end 变为 word_assigned 或 registered
    // 2. 并且回合号重置为1（这是新游戏开始的标志，因为每次新游戏开始时回合号都会重置为1）
    const isNewGame = lastGameStatus === 'game_end' && 
                      (currentStatus === 'word_assigned' || currentStatus === 'registered') &&
                      currentRound === 1;
    
    // 只有当有轮次配置且回合号大于0时，才建立回合号到轮次的映射
    // 只在真正的新游戏开始时建立映射，避免在同一个轮次内重复更新映射
    // 只在状态从 game_end 变为 word_assigned 且回合号为1时，才建立映射
    if (currentRound > 0 && gameNumber && isNewGame && currentRound === 1) {
        // 只在新游戏开始时建立映射，避免覆盖已有映射
        if (!descriptionRoundMapping[currentRound]) {
            descriptionRoundMapping[currentRound] = gameNumber;
        }
        
        if (!voteRoundMapping[currentRound]) {
            voteRoundMapping[currentRound] = gameNumber;
        }
    }
    
    // 不再在 updateAllDisplay() 中处理描述记录
    // 描述记录只在 descriptions_update WebSocket 事件中存储（参考投票记录的机制）
    // 这样可以确保只在正确的时机使用正确的轮次号存储描述
    
    // 更新跟踪变量
    lastGameStatus = currentStatus;
    lastCurrentRound = currentRound;
    lastGameNumber = gameNumber;
    
    updateGameStatus();
    updatePlayers();
    updateDescriptions();
    updateVoteRecords();
    updateGameResults();
    updateGameStats();
    updateGameStateDisplay(gameData); 
    updateRealTimeInfo(gameData);
    updateBottomCounters(); 
}

function updateBottomCounters() {
    // 从当前的 gameData 中获取数据
    const describedCount = gameData.described_groups?.length || 0;
    const orderCount = gameData.describe_order?.length || 0;
    const votedCount = gameData.voted_groups?.length || 0;
    const activeCount = gameData.active_groups?.length || orderCount;

    document.getElementById('desc-count').textContent = `${describedCount}/${orderCount}`;
    document.getElementById('vote-count').textContent = `${votedCount}/${activeCount}`;
}

function updateGameStatus() {
    const status = gameData.status || 'waiting';
    const statusMap = {
        'waiting': '准备中',
        'registered': '准备中',
        'word_assigned': '准备中',
        'describing': '描述中',
        'voting': '投票中',
        'round_end': '回合结束',
        'game_end': '游戏结束'
    };

    document.getElementById('game-status').textContent = statusMap[status] || status;
    document.getElementById('stat-round').textContent = gameData.current_round || 0;
}

function updatePlayers() {
    const playersGrid = document.getElementById('players-grid');
    const groups = gameData.groups || {};
    const gameStatus = gameData.status || 'waiting';

    document.getElementById('player-count').textContent = Object.keys(groups).length;

    if (Object.keys(groups).length === 0) {
        playersGrid.innerHTML = `
            <div class="player-card">
                <div class="player-header">
                    <div class="player-name">等待玩家注册...</div>
                </div>
            </div>
        `;
        return;
    }

    let html = '';
    const currentSpeaker = gameData.current_speaker || '';
    const eliminatedGroups = gameData.eliminated_groups || [];
    const describedGroups = gameData.described_groups || [];
    const votedGroups = gameData.voted_groups || [];
    const onlineStatus = gameData.online_status || {};
    const round = gameData.current_round;

    // 按得分排序
    const sortedGroups = Object.entries(groups).sort((a, b) => {
        const scoreA = gameData.scores?.[a[0]] || 0;
        const scoreB = gameData.scores?.[b[0]] || 0;
        return scoreB - scoreA;
    });

    sortedGroups.forEach(([name, info]) => {
        const isEliminated = eliminatedGroups.includes(name) || info.eliminated;

        const isUndercover = (gameStatus === 'word_assigned' || 
                             gameStatus === 'describing' || 
                             gameStatus === 'voting' || 
                             gameStatus === 'round_end' || 
                             gameStatus === 'game_end') 
                             ? (info.role === 'undercover') 
                             : false;

        const isCurrentSpeaker = currentSpeaker === name;
        const hasDescribed = describedGroups.includes(name);
        const hasVoted = votedGroups.includes(name);
        const isOnline = onlineStatus[name] !== false;
        const score = gameData.scores?.[name] || 0;

        // 获取当前回合的描述
        let currentDescription = '';
        let currentVote = '';

        if (gameData.descriptions && gameData.descriptions[round]) {
            const desc = gameData.descriptions[round].find(d => d.group === name);
            if (desc) {
                currentDescription = desc.description;
            }
        }

        if (gameData.votes && gameData.votes[round]) {
            currentVote = gameData.votes[round][name] || '';
        }

        // 构建角色显示逻辑
        let roleDisplay = '';
        let roleBadge = '';

        if (gameStatus === 'word_assigned' || 
            gameStatus === 'describing' || 
            gameStatus === 'voting' || 
            gameStatus === 'round_end' || 
            gameStatus === 'game_end') {
            
            if (info.role) {
                const isUndercoverRole = info.role === 'undercover';
                roleDisplay = isUndercoverRole ? '<i class="fas fa-user-secret"></i>' : '';
                roleBadge = `
                    <div class="player-role ${isUndercoverRole ? 'role-undercover' : 'role-civilian'}">
                        ${isUndercoverRole ? '卧底' : '平民'}
                    </div>
                `;
            }
        } else {
            roleBadge = `
                <div class="player-role" style="background: #95a5a6; color: white;">
                    未开始
                </div>
            `;
        }

        // 玩家卡片
        html += `
            <div class="player-card ${isUndercover ? 'undercover' : ''} ${isEliminated ? 'eliminated' : ''} ${isCurrentSpeaker ? 'current-turn' : ''}">
                <div class="player-header">
                    <div class="player-name">
                        ${name} ${roleDisplay}
                    </div>
                    ${roleBadge}
                </div>

                <div class="player-status">
                    ${isCurrentSpeaker ? '<span class="status-badge status-speaking">发言中</span>' : ''}
                    ${hasDescribed && !isCurrentSpeaker ? '<span class="status-badge status-described">已描述</span>' : ''}
                    ${hasVoted ? '<span class="status-badge status-voted">已投票</span>' : ''}
                    ${(gameStatus === 'word_assigned' || gameStatus === 'round_end') && (gameData.ready_groups || []).includes(name) ? '<span class="status-badge status-ready">已准备</span>' : ''}
                    <span class="status-badge ${isOnline ? 'status-online' : 'status-offline'}">
                        ${isOnline ? '在线' : '离线'}
                    </span>
                </div>

                <!-- 玩家信息栏 -->
                <div class="player-info">
                    <span>总分: ${score}</span>
                    <span>卧底: ${info.undercover_count || 0}次</span>
                </div>

                ${currentDescription ? `
                    <div class="player-content">
                        <div class="player-description">
                            <strong>描述:</strong> ${currentDescription}
                        </div>
                    </div>
                ` : ''}

                ${currentVote ? `
                    <div class="player-content">
                        <div class="player-vote">
                            <strong>投票给:</strong> ${currentVote}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    });

    playersGrid.innerHTML = html;
}

function updateDescriptions() {
    const container = document.getElementById('descriptions-content');
    // 如果 allDescriptions 为空，显示暂无记录
    if (Object.keys(allDescriptions).length === 0) {
        container.innerHTML = `
            <div class="description-item">
                <div class="desc-header">暂无描述记录</div>
            </div>
        `;
        return;
    }
    // 使用历史描述记录
    // 判断是否是多轮游戏：检查是否有包含下划线的键（多轮格式）
    const hasMultiRoundKeys = Object.keys(allDescriptions).some(key => key.includes('_'));
    
    const descriptionsToDisplay = {};
    
    Object.keys(allDescriptions).forEach(key => {
        if (hasMultiRoundKeys) {
            // 如果有多轮格式的键，只显示多轮格式的记录（包含下划线的键，如 "1_1", "2_1"）
            if (key.includes('_')) {
                descriptionsToDisplay[key] = allDescriptions[key];
            }
        } else {
            // 单轮游戏：显示所有格式的记录
            descriptionsToDisplay[key] = allDescriptions[key];
        }
    });

    if (Object.keys(descriptionsToDisplay).length === 0) {
        container.innerHTML = `
            <div class="description-item">
                <div class="desc-header">暂无描述记录</div>
            </div>
        `;
        return;
    }

    let html = '';
    const undercoverGroup = gameData.undercover_group;

    // 按顺序排列（最新的在前）
    // 首先按轮次排序，然后按回合排序
    const descriptionEntries = Object.entries(descriptionsToDisplay).map(([key, roundDescriptions]) => {
        // 解析键：如果是 "gameNumber_round" 格式，提取轮次和回合
        const parts = key.toString().split('_');
        let gameNumber = null;
        let round = null;
        
        if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
            // 多轮格式：gameNumber_round
            gameNumber = parseInt(parts[0]);
            round = parseInt(parts[1]);
        } else {
            // 单轮格式：只有 round
            round = parseInt(key);
            gameNumber = descriptionRoundMapping[round] || null;
        }
        
        return {
            round: round,
            gameNumber: gameNumber || 999, // 单轮游戏放到最后
            roundDescriptions: roundDescriptions
        };
    });
    
    // 排序：先按轮次降序，再按回合降序
    descriptionEntries.sort((a, b) => {
        if (a.gameNumber !== b.gameNumber) {
            return b.gameNumber - a.gameNumber;
        }
        return b.round - a.round;
    });

    descriptionEntries.forEach(({round, gameNumber, roundDescriptions}) => {
        if (!roundDescriptions || roundDescriptions.length === 0) return;

        // 确定这个回合属于第几轮
        const displayGameNumber = gameNumber !== 999 ? gameNumber : null;
        let titleText = '';
        // 判断是否显示轮次：如果有多轮格式的键，就按多轮格式显示
        if (hasMultiRoundKeys) {
            // 多轮游戏：必须显示轮次
            if (displayGameNumber !== null) {
                titleText = `第 ${displayGameNumber} 轮第 ${round} 回合 - ${roundDescriptions.length} 个描述`;
            } else {
                // 如果没有轮次信息，跳过这条记录（多轮游戏不应该出现这种情况）
                return;
            }
        } else {
            // 单轮游戏：不显示轮次
            titleText = `第 ${round} 回合 - ${roundDescriptions.length} 个描述`;
        }

        html += `
            <div class="round-vote-section">
                <div class="round-title">${titleText}</div>
        `;

        roundDescriptions.forEach(desc => {
            const isUndercover = desc.group === undercoverGroup;
            // 安全地解析时间，如果时间无效则显示空字符串
            let timeStr = '';
            if (desc.time) {
                try {
                    const timeDate = new Date(desc.time);
                    if (!isNaN(timeDate.getTime())) {
                        timeStr = timeDate.toLocaleTimeString('zh-CN', { 
                            hour: '2-digit', 
                            minute: '2-digit',
                            second: '2-digit'
                        });
                    }
                } catch (e) {
                    console.warn('时间解析失败:', desc.time, e);
                }
            }

            html += `
                <div class="description-item ${isUndercover ? 'undercover' : ''}">
                    <div class="desc-header">
                        <span>${desc.group} ${isUndercover ? '<i class="fas fa-user-secret"></i>' : ''}</span>
                        ${timeStr ? `<span style="color: #7f8c8d; font-size: 0.9em;">${timeStr}</span>` : ''}
                    </div>
                    <div class="desc-text">${desc.description}</div>
                </div>
            `;
        });

        html += `</div>`;
    });

    container.innerHTML = html || '<div class="description-item"><div class="desc-header">暂无描述记录</div></div>';
}

function updateVoteRecords() {
    const container = document.getElementById('votes-content');
    // 如果 allVoteResults 为空，显示暂无记录
    if (Object.keys(allVoteResults).length === 0) {
        container.innerHTML = `
            <div class="round-vote-section">
                <div class="round-title">暂无投票记录</div>
            </div>
        `;
        return;
    }
    // 只使用 allVoteResults 中的数据，不再从 gameData.votes 添加
    // 因为投票结果已经通过 vote_result 事件存储在 allVoteResults 中了
    const allVotes = { ...allVoteResults };

    if (Object.keys(allVotes).length === 0) {
        container.innerHTML = `
            <div class="round-vote-section">
                <div class="round-title">暂无投票记录</div>
            </div>
        `;
        return;
    }

    let html = '';

    // 按顺序排列（最新的在前）
    // 首先按轮次排序，然后按回合排序
    const voteEntries = Object.entries(allVotes).map(([key, voteData]) => {
        // 解析键：如果是 "gameNumber_round" 格式，提取轮次和回合
        const parts = key.toString().split('_');
        let gameNumber = null;
        let round = null;
        
        if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
            gameNumber = parseInt(parts[0]);
            round = parseInt(parts[1]);
        } else {
            round = parseInt(key);
            gameNumber = voteRoundMapping[round] || (voteData.game_number || null);
        }
        
        return {
            key: key,
            gameNumber: gameNumber || 999, // 单轮游戏放到最后
            round: round,
            voteData: voteData
        };
    });
    
    // 排序：先按轮次降序，再按回合降序
    voteEntries.sort((a, b) => {
        if (a.gameNumber !== b.gameNumber) {
            return b.gameNumber - a.gameNumber;
        }
        return b.round - a.round;
    });

    voteEntries.forEach(({key, gameNumber, round, voteData}) => {
        // 确定这个回合属于第几轮
        const displayGameNumber = gameNumber !== 999 ? gameNumber : null;
        
        let titleText = '';
        // 判断是否显示轮次：如果有轮次信息且不是默认值，就显示
        if (displayGameNumber !== null) {
            titleText = `第 ${displayGameNumber} 轮第 ${round} 回合投票记录`;
        } else {
            titleText = `第 ${round} 回合投票记录`;
        }

        html += `
            <div class="round-vote-section">
                <div class="round-title">${titleText}</div>
        `;

        // 显示每个人的投票
        if (voteData.vote_details) {
            html += `<div style="margin-bottom: 10px;"><strong>投票详情:</strong></div>`;
            Object.entries(voteData.vote_details).forEach(([voter, target]) => {
                html += `
                    <div class="vote-item">
                        <div class="vote-from">${voter}</div>
                        <i class="fas fa-arrow-right" style="color: #7f8c8d;"></i>
                        <div class="vote-to">${target}</div>
                    </div>
                `;
            });
        }

        // 显示得票统计
        if (voteData.vote_count && Object.keys(voteData.vote_count).length > 0) {
            html += `<div style="margin-top: 10px;"><strong>得票统计:</strong></div>`;
            Object.entries(voteData.vote_count).forEach(([group, count]) => {
                html += `
                    <div class="vote-count-item">
                        <div>${group}</div>
                        <div style="color: var(--warning-color); font-weight: bold;">${count} 票</div>
                    </div>
                `;
            });
        }

        html += `</div>`;
    });

    container.innerHTML = html;
}

function updateGameResults() {
    const container = document.getElementById('results-content');
    // 如果 allVoteResults 为空，显示暂无记录
    if (Object.keys(allVoteResults).length === 0) {
        container.innerHTML = `
            <div class="result-item">
                <div class="result-header">暂无游戏结果</div>
            </div>
        `;
        return;
    }
    if (Object.keys(allVoteResults).length === 0) {
        container.innerHTML = `
            <div class="result-item">
                <div class="result-header">暂无游戏结果</div>
            </div>
        `;
        return;
    }

    let html = '';

    // 按顺序排列结果（最新的在前）
    // 首先按轮次排序，然后按回合排序
    const results = Object.entries(allVoteResults).map(([key, result]) => {
        // 解析键：如果是 "gameNumber_round" 格式，提取轮次和回合
        const parts = key.split('_');
        let gameNumber = null;
        let round = null;
        
        if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
            gameNumber = parseInt(parts[0]);
            round = parseInt(parts[1]);
        } else {
            round = parseInt(key);
            // 使用与投票记录相同的逻辑：优先从 voteRoundMapping 获取
            gameNumber = voteRoundMapping[round] || (result.game_number || null);
        }
        
        return {
            key: key,
            gameNumber: gameNumber || 999, // 单轮游戏放到最后
            round: round,
            result: result
        };
    });
    
    // 排序：先按轮次降序，再按回合降序
    results.sort((a, b) => {
        if (a.gameNumber !== b.gameNumber) {
            return b.gameNumber - a.gameNumber;
        }
        return b.round - a.round;
    });
    
    results.forEach(({key, gameNumber, round, result}) => {
        const roundScores = result.round_scores || {};
        const totalScores = result.total_scores || {};
        
        // 构建标题：使用与投票记录和描述记录相同的逻辑
        const displayGameNumber = gameNumber !== 999 ? gameNumber : null;
        let titleText = '';
        // 判断是否显示轮次：如果有轮次信息且不是默认值，就显示（不管multiRoundConfig是否存在）
        if (displayGameNumber !== null && displayGameNumber !== 999) {
            titleText = `第 ${displayGameNumber} 轮第 ${round} 回合结果`;
        } else {
            titleText = `第 ${round} 回合结果`;
        }

        html += `
            <div class="result-item ${result.game_ended ? 'victory' : ''}">
                <div class="result-header">
                    <span>${titleText}</span>
                    <span style="color: ${result.game_ended ? (result.winner === 'undercover' ? 'var(--danger-color)' : 'var(--secondary-color)') : 'var(--warning-color)'}">
                        ${result.game_ended ? (result.winner === 'undercover' ? '🎭 卧底胜利' : '👥 平民胜利') : '游戏继续'}
                    </span>
                </div>
                <div class="result-details">
        `;

        // 显示淘汰信息
        if (result.eliminated && result.eliminated.length > 0) {
            html += `
                <div style="margin-bottom: 5px;">
                    <i class="fas fa-skull-crossbones" style="color: var(--danger-color);"></i>
                    <strong>被淘汰:</strong> ${result.eliminated.join(', ')}
                </div>
            `;
        }

        // 显示本轮各组成绩
        if (result.round_scores && Object.keys(result.round_scores).length > 0) {
            html += `
                <div style="margin: 10px 0; padding: 10px; background: rgba(0,0,0,0.05); border-radius: 5px;">
                    <strong><i class="fas fa-star"></i> 本轮得分:</strong>
            `;

            Object.entries(result.round_scores).forEach(([group, score]) => {
                // 区分得分类型
                let scoreType = '生存分';
                if (result.game_ended && result.winner === 'undercover' && group === result.undercover_group) {
                    if (score >= 4) {  // 1生存分 + 3胜利分
                        scoreType = '生存分+胜利分';
                    }
                }

                html += `
                    <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                        <span>${group} <small style="color: #7f8c8d">(${scoreType})</small></span>
                        <span style="font-weight: bold; color: ${score > 0 ? 'var(--secondary-color)' : '#7f8c8d'}">
                            ${score > 0 ? '+' : ''}${score}分
                        </span>
                    </div>
                `;
            });

            html += `</div>`;
        }

        // 显示累计得分
        if (Object.keys(totalScores).length > 0) {
            html += `
                <div style="margin: 10px 0; padding: 10px; background: rgba(243, 156, 18, 0.1); border-radius: 5px;">
                    <strong><i class="fas fa-trophy"></i> 累计得分:</strong>
            `;

            // 按分数排序
            const sortedScores = Object.entries(totalScores).sort((a, b) => b[1] - a[1]);

            sortedScores.forEach(([group, score], index) => {
                const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '';
                html += `
                    <div style="display: flex; justify-content: space-between; padding: 3px 0; ${index === 0 ? 'font-weight: bold;' : ''}">
                        <span>${medal} ${group}</span>
                        <span style="color: var(--warning-color)">${score}分</span>
                    </div>
                `;
            });

            html += `</div>`;
        }

        // 显示最高票数
        if (result.max_voted_groups && result.max_voted_groups.length > 0) {
            html += `
                <div style="margin-bottom: 5px;">
                    <i class="fas fa-chart-bar" style="color: var(--warning-color);"></i>
                    <strong>最高票:</strong> ${result.max_voted_groups.join(', ')} (${result.max_votes || 0}票)
                </div>
            `;
        }

        // 显示游戏结束信息
        if (result.game_ended) {
            html += `
                <div style="margin-bottom: 5px;">
                    <i class="fas fa-flag" style="color: var(--secondary-color);"></i>
                    <strong>游戏结束:</strong> ${result.message || ''}
                </div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-color);">
                    <div><strong>卧底词:</strong> ${result.undercover_word || '未知'}</div>
                    <div><strong>平民词:</strong> ${result.civilian_word || '未知'}</div>
                    <div><strong>卧底:</strong> ${result.undercover_group || '未知'}</div>
                </div>
            `;
            
            // 注意：checkAndStartNextRound() 已经在 vote_result 事件处理中调用，这里不需要重复调用
        }

        html += `</div></div>`;
    });

    container.innerHTML = html;
}

function updateGameStats() {
    const groups = gameData.groups || {};
    const scores = gameData.scores || {};

    // 注册组数 - 保持不变
    document.getElementById('stat-groups').textContent = Object.keys(groups).length;

    // 游戏次数 - 从后端获取，重置后应该为0
    document.getElementById('stat-games').textContent = gameData.game_counter || 0;

    // 当前回合 - 从后端获取，重置后应该为0
    document.getElementById('stat-round').textContent = gameData.current_round || 0;

    // 最高分 - 重置后所有分数为0，所以最高分也是0
    const scoresArray = Object.values(scores);
    const maxScore = scoresArray.length > 0 ? Math.max(...scoresArray) : 0;
    document.getElementById('stat-highscore').textContent = maxScore;
}

function updateRealTimeInfo(data) {
    // 更新当前发言者
    const currentSpeaker = data.current_speaker || '--';
    document.getElementById('current-speaker-name').textContent = currentSpeaker;

    // 更新计数
    const describedGroups = data.described_groups || [];
    const describeOrder = data.describe_order || [];
    const votedGroups = data.voted_groups || [];
    const activeGroups = data.active_groups || [];

    // 描述完成人数
    const describedCount = describedGroups.length;
    const orderCount = describeOrder.length;

    // 投票完成人数
    const votedCount = votedGroups.length;
    const activeCount = activeGroups.length || orderCount;

    document.getElementById('desc-count').textContent = `${describedCount}/${orderCount}`;
    document.getElementById('vote-count').textContent = `${votedCount}/${activeCount}`;

    // 更新游戏状态显示
    updateGameStateDisplay(data);
}

function updateGameStateDisplay(data) {
    const displayElement = document.getElementById('game-state-display');
    
    // 检查displayElement是否存在
    if (!displayElement) {
        console.warn('game-state-display 元素未找到');
        return;
    }
    
    const status = data.status || 'waiting';
    const currentSpeaker = data.current_speaker || '';
    const describedGroups = data.described_groups || [];
    const votedGroups = data.voted_groups || [];
    const describeOrder = data.describe_order || [];
    const activeGroups = data.active_groups || [];
    const currentRound = data.current_round || 1;
    const eliminatedGroups = data.eliminated_groups || [];
    const currentSpeakerIndex = data.current_speaker_index || 0;

    let displayText = '';
    let displayClass = '';
    let bgColor = '';

    const latestRound = Math.max(...Object.keys(allVoteResults).map(Number).filter(n => !isNaN(n)), 0);
    const latestResult = latestRound > 0 ? allVoteResults[latestRound] : null;

    switch(status) {
        case 'waiting':
        case 'registered':
        case 'word_assigned':
            const readyGroups = data.ready_groups || [];
            if (readyGroups.length > 0 && activeGroups.length > 0) {
                displayText = `🎮 等待准备 (${readyGroups.length}/${activeGroups.length})`;
            } else {
                displayText = '🎮 准备中...';
            }
            displayClass = 'state-preparing';
            bgColor = 'rgba(52, 152, 219, 0.1)';
            break;

        case 'describing':
            if (describeOrder.length > 0) {
                let html = '<div style="display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 8px; margin-left: 20px;">';

                describeOrder.forEach((group, index) => {
                    const isCurrent = group === currentSpeaker;
                    const isEliminated = eliminatedGroups.includes(group);
                    const hasDescribed = describedGroups.includes(group);
                    const isBeforeCurrent = index < currentSpeakerIndex;

                    let text = group;
                    let style = '';

                    if (isEliminated) {
                        style = `
                            padding: 3px 8px;
                            border-radius: 4px;
                            font-size: 0.9em;
                            background: #95a5a6;
                            color: white;
                            font-weight: normal;
                            border: 1px solid var(--border-color);
                            opacity: 0.7;
                        `;
                        text = '💀 ' + text;
                    } else if (isCurrent) {
                        style = `
                            padding: 5px 10px;
                            border-radius: 6px;
                            font-size: 1.1em;
                            background: var(--primary-color);
                            color: white;
                            font-weight: bold;
                            border: 2px solid var(--primary-color);
                            animation: pulse-border 1.5s infinite;
                            box-shadow: 0 0 10px rgba(52, 152, 219, 0.5);
                        `;
                        text = '🎤 ' + text;
                    } else if (isBeforeCurrent || hasDescribed) {
                        style = `
                            padding: 3px 8px;
                            border-radius: 4px;
                            font-size: 0.9em;
                            background: #2ecc71;
                            color: white;
                            font-weight: normal;
                            border: 1px solid var(--border-color);
                        `;
                        text = '✅ ' + text;
                    } else {
                        style = `
                            padding: 3px 8px;
                            border-radius: 4px;
                            font-size: 0.9em;
                            background: var(--light-color);
                            color: var(--dark-color);
                            font-weight: normal;
                            border: 1px solid var(--border-color);
                        `;
                        text = '⬜ ' + text;
                    }

                    html += `<span style="${style}">${text}</span>`;

                    if (index < describeOrder.length - 1) {
                        html += `<span style="color: #7f8c8d; font-size: 1.2em; margin: 0 4px;">→</span>`;
                    }
                });

                html += '</div>';
                displayText = `🗣️ 描述中：${html}`;
                displayClass = 'state-describing';
                bgColor = 'rgba(52, 152, 219, 0.15)';
            } else {
                displayText = `🗣️ 描述阶段...`;
                displayClass = 'state-describing';
                bgColor = 'rgba(52, 152, 219, 0.15)';
            }
            break;

        case 'voting':
            // 投票阶段：显示投票进度
            const votedCount = votedGroups.length;
            const totalCount = activeGroups.length || describeOrder.length;

            displayText = `🗳️ 投票中 (${votedCount}/${totalCount})`;
            displayClass = 'state-voting';
            console.log('投票阶段 displayText:', displayText);

            if (votedCount >= totalCount && totalCount > 0) {
                bgColor = 'rgba(46, 204, 113, 0.2)';
            } else if (votedCount >= Math.ceil(totalCount / 2)) {
                bgColor = 'rgba(243, 156, 18, 0.2)';
            } else {
                bgColor = 'rgba(243, 156, 18, 0.15)';
            }
            break;

        case 'round_end':
            const readyGroupsRound = data.ready_groups || [];
            if (readyGroupsRound.length > 0 && activeGroups.length > 0) {
                displayText = `🏁 回合结束，等待准备 (${readyGroupsRound.length}/${activeGroups.length})`;
            } else {
                if (latestResult) {
                    if (latestResult.eliminated && latestResult.eliminated.length > 0) {
                        displayText = `🏁 ${latestResult.eliminated.join(', ')} 被淘汰，游戏继续`;
                    } else {
                        displayText = '🏁 无人淘汰，游戏继续';
                    }
                } else {
                    displayText = `🏁 第${currentRound}回合结束`;
                }
            }
            displayClass = 'state-round-end';
            bgColor = 'rgba(155, 89, 182, 0.1)';
            break;

        case 'game_end':
            let winnerText = '';
            let winner = '';

            if (latestResult) {
                winner = latestResult.winner || '';
            }

            if (winner === 'undercover' || winner === '卧底') {
                winnerText = '🎭 卧底胜利';
                bgColor = 'rgba(231, 76, 60, 0.1)';
                displayClass = 'state-game-end undercover-victory';
            } else {
                winnerText = '👥 平民胜利';
                bgColor = 'rgba(46, 204, 113, 0.1)';
                displayClass = 'state-game-end civilian-victory';
            }
            displayText = `🎊 游戏结束 - ${winnerText}`;
            break;

        default:
            displayText = `🔄 ${status}`;
            displayClass = 'state-other';
            bgColor = 'rgba(149, 165, 166, 0.1)';
    }

    // 更新显示内容
    console.log('displayText:', displayText, 'displayClass:', displayClass);
    displayElement.innerHTML = displayText;
    displayElement.className = 'game-state-display ' + displayClass;
    displayElement.style.background = bgColor;

    // 只在描述阶段更新当前发言者，其他阶段清除
    if (status === 'describing' && currentSpeaker) {
        document.getElementById('current-speaker-name').textContent = currentSpeaker;
        document.getElementById('current-speaker-name').style.color = 'var(--primary-color)';
    } else if (status !== 'describing') {
        // 非描述阶段，清除当前发言者显示（避免残留）
        document.getElementById('current-speaker-name').textContent = '--';
        document.getElementById('current-speaker-name').style.color = '';
    }
}

function updateTimers(data) {
    const mainTimer = document.getElementById('main-timer');
    const descTimer = document.getElementById('desc-timer-display');
    const voteTimer = document.getElementById('vote-timer-display');

    // 检查元素是否存在
    if (!descTimer || !voteTimer) {
        console.warn('倒计时元素未找到:', {descTimer, voteTimer});
        return;
    }

    // 清除所有警告样式
    if (mainTimer) {
        mainTimer.classList.remove('timer-warning');
        mainTimer.style.color = '';
    }

    // 主计时器
    if (data.status === 'describing') {
        if (data.speaker_remaining_seconds !== undefined && data.speaker_remaining_seconds >= 0) {
            if (mainTimer) mainTimer.textContent = `${data.speaker_remaining_seconds}s`;

            // 左侧倒计时显示
            descTimer.textContent = `${data.speaker_remaining_seconds}s`;
            voteTimer.textContent = '--:--';

            // 最后10秒红色闪烁
            if (data.speaker_remaining_seconds <= 10) {
                if (mainTimer) {
                    mainTimer.classList.add('timer-warning');
                    mainTimer.style.color = 'var(--danger-color)';
                }
                descTimer.style.color = 'var(--danger-color)';
            } else {
                descTimer.style.color = '';
            }
        } else if (data.remaining_seconds !== undefined && data.remaining_seconds >= 0) {
            const timeStr = formatTime(data.remaining_seconds);

            if (mainTimer) mainTimer.textContent = timeStr;
            descTimer.textContent = timeStr;
            voteTimer.textContent = '--:--';

            if (data.remaining_seconds <= 10) {
                if (mainTimer) {
                    mainTimer.classList.add('timer-warning');
                    mainTimer.style.color = 'var(--danger-color)';
                }
                descTimer.style.color = 'var(--danger-color)';
            } else {
                descTimer.style.color = '';
            }
        } else {
            // 没有倒计时数据时
            if (mainTimer) mainTimer.textContent = '--:--';
            descTimer.textContent = '--:--';
            voteTimer.textContent = '--:--';
            descTimer.style.color = '';
            voteTimer.style.color = '';
        }
    } else if (data.status === 'voting') {
        if (data.remaining_seconds !== undefined && data.remaining_seconds >= 0) {
            const timeStr = formatTime(data.remaining_seconds);

            if (mainTimer) mainTimer.textContent = timeStr;
            descTimer.textContent = '--:--';
            voteTimer.textContent = timeStr;

            if (data.remaining_seconds <= 10) {
                if (mainTimer) {
                    mainTimer.classList.add('timer-warning');
                    mainTimer.style.color = 'var(--danger-color)';
                }
                voteTimer.style.color = 'var(--danger-color)';
            } else {
                voteTimer.style.color = '';
            }
        } else {
            if (mainTimer) mainTimer.textContent = '--:--';
            descTimer.textContent = '--:--';
            voteTimer.textContent = '--:--';
            descTimer.style.color = '';
            voteTimer.style.color = '';
        }
    } else {
        if (mainTimer) mainTimer.textContent = '--:--';
        descTimer.textContent = '--:--';
        voteTimer.textContent = '--:--';
        descTimer.style.color = '';
        voteTimer.style.color = '';
    }
}

function formatTime(seconds) {
    if (seconds === undefined || seconds < 0) return '--:--';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateServerStatus(isConnected) {
    const statusElement = document.getElementById('server-status');
    statusElement.textContent = '已连接';
    statusElement.style.color = 'var(--secondary-color)';
}

// 标签页切换函数
function switchTab(tabName) {
    // 切换导航按钮状态
    document.querySelectorAll('.tab-nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // 切换内容面板
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.getElementById('tab-' + tabName).classList.add('active');
}

function showAlert(type, message) {
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    // 创建新的提示
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 
                           type === 'danger' ? 'exclamation-triangle' : 
                           type === 'warning' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${message}
    `;

    document.body.appendChild(alert);

    // 3秒后自动移除
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 3000);
}

// 多轮游戏配置
function openMultiRoundModal() {
    const modal = document.getElementById('multiRoundModal');
    modal.classList.add('show');
    // 初始化默认值
    document.getElementById('round-count').value = '1';
    generateRoundInputs();
}

function closeMultiRoundModal() {
    const modal = document.getElementById('multiRoundModal');
    modal.classList.remove('show');
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('multiRoundModal');
    if (event.target === modal) {
        closeMultiRoundModal();
    }
}

function generateRoundInputs() {
    const roundCount = parseInt(document.getElementById('round-count').value) || 1;
    const container = document.getElementById('rounds-container');
    
    // 限制轮数范围
    if (roundCount < 1) {
        document.getElementById('round-count').value = '1';
        return;
    }
    if (roundCount > 10) {
        document.getElementById('round-count').value = '10';
        return;
    }

    let html = '';
    for (let i = 1; i <= roundCount; i++) {
        html += `
            <div class="round-item">
                <div class="round-item-header">
                    <i class="fas fa-circle"></i>
                    第 ${i} 轮
                </div>
                <div class="round-item-inputs">
                    <div class="round-item-input">
                        <label for="undercover-word-round-${i}">
                            <i class="fas fa-user-secret"></i> 卧底词
                        </label>
                        <input type="text" id="undercover-word-round-${i}" 
                               placeholder="输入第${i}轮的卧底词" required>
                    </div>
                    <div class="round-item-input">
                        <label for="civilian-word-round-${i}">
                            <i class="fas fa-users"></i> 平民词
                        </label>
                        <input type="text" id="civilian-word-round-${i}" 
                               placeholder="输入第${i}轮的平民词" required>
                    </div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}

function submitMultiRoundGame() {
    const roundCount = parseInt(document.getElementById('round-count').value) || 1;
    
    // 收集所有轮次的词语（允许为空，后端会自动选词）
    const rounds = [];
    
    for (let i = 1; i <= roundCount; i++) {
        const undercoverWord = document.getElementById(`undercover-word-round-${i}`).value.trim();
        const civilianWord = document.getElementById(`civilian-word-round-${i}`).value.trim();
        
        rounds.push({
            round: i,
            undercover_word: undercoverWord,
            civilian_word: civilianWord
        });
    }
    
    // 设置总轮数和当前轮次索引
    totalRounds = roundCount;
    currentRoundIndex = 0;
    multiRoundConfig = rounds; // 保存配置用于获取词语
    
    // 关闭模态框
    closeMultiRoundModal();
    
    // 显示提示
    showAlert('info', `已配置 ${roundCount} 轮游戏，准备开始第 1 轮...`);
    
    // 开始第一轮游戏
    const firstRound = rounds[0];
    startGameWithWords(firstRound.undercover_word, firstRound.civilian_word, true);
}

// 多轮游戏计数系统（重构后）
let totalRounds = 0; // 总轮数（从配置中获取，如3表示要玩3轮）
let currentRoundIndex = 0; // 当前轮次索引（从0开始，0表示第1轮，1表示第2轮，以此类推）
let nextRoundCheckDone = false; // 防止重复触发下一轮检查
let multiRoundConfig = null; // 保留配置用于获取词语，但不再依赖其长度来判断

function startGameWithWords(undercoverWord, civilianWord, isFirstRound = false) {
    if (isFirstRound) {
        // 新开始游戏（第一轮或单轮游戏）：清空所有历史数据
        allVoteResults = {};
        allDescriptions = {}; // 新游戏开始时清空描述记录
        gameRoundMapping = {};
        descriptionRoundMapping = {};
        voteRoundMapping = {};
        nextRoundCheckDone = false; // 重置下一轮检查标志
    }
    // 如果是多轮游戏的第二轮及之后（isFirstRound = false），不清空 allDescriptions，保留历史记录
    
    // 保存状态到 localStorage
    saveToLocalStorage();
    
    fetch('/api/game/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            undercover_word: undercoverWord,
            civilian_word: civilianWord
        })
    })
    .then(response => response.json())
    .then(resp => {
        if (resp && resp.code === 200) {
            showAlert('success', resp.message || '游戏已开始！');
            nextRoundCheckDone = false; // 新游戏开始，重置检查标志
            // 显示自动选择的词语
            if (resp.data && resp.data.civilian_word && resp.data.undercover_word) {
                document.getElementById('civilian-word').value = resp.data.civilian_word;
                document.getElementById('undercover-word').value = resp.data.undercover_word;
            }
            fetchGameState();
        } else {
            showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
        }
    })
    .catch(error => {
        showAlert('danger', '请求失败：' + error);
    });
}

// 检查并开始下一轮游戏（重构后的简化逻辑）
function checkAndStartNextRound() {
    // 防止重复触发
    if (nextRoundCheckDone) {
        return;
    }
    
    // 如果没有配置多轮游戏，直接返回
    if (totalRounds <= 0) {
        return;
    }

    // 标记为已检查，防止重复
    nextRoundCheckDone = true;

    // 检查是否还有下一轮：currentRoundIndex < totalRounds - 1
    // 例如：totalRounds=3, currentRoundIndex=0 -> 还有第2、3轮
    //      totalRounds=3, currentRoundIndex=1 -> 还有第3轮
    //      totalRounds=3, currentRoundIndex=2 -> 没有下一轮了
    if (currentRoundIndex >= totalRounds - 1) {
        // 所有轮次都已完成
        showAlert('info', `所有 ${totalRounds} 轮游戏已完成！`);
        // 清空配置
        totalRounds = 0;
        currentRoundIndex = 0;
        multiRoundConfig = null;
        saveToLocalStorage();
        return;
    }

    // 延迟3秒后自动开始下一轮，给用户时间查看结果
    setTimeout(() => {
        // 递增当前轮次索引
        currentRoundIndex++;
        
        // 获取当前轮次的词语配置
        const nextRound = multiRoundConfig[currentRoundIndex];
        
        // 保存到 localStorage
        saveToLocalStorage();
        
        showAlert('info', `准备开始第 ${currentRoundIndex + 1} 轮游戏...`);
        
        // 开始下一轮游戏（不清空历史数据，回合号由后端继续递增）
        startGameWithWords(
            nextRound.undercover_word, 
            nextRound.civilian_word,
            false // 不是第一轮
        );
    }, 3000);
}

// 开始单轮游戏（从输入框获取词语）
function startSingleGame() {
    const undercoverWord = document.getElementById('undercover-word').value.trim();
    const civilianWord = document.getElementById('civilian-word').value.trim();
    
    // 允许词语为空，后端会自动从词库选择
    // if (!undercoverWord || !civilianWord) {
    //     showAlert('danger', '请输入卧底词和平民词');
    //     return;
    // }
    
    // 清空多轮配置（单轮游戏不需要多轮配置）
    totalRounds = 0;
    currentRoundIndex = 0;
    multiRoundConfig = null;
    nextRoundCheckDone = false;
    
    // 清空历史数据
    allVoteResults = {};
    allDescriptions = {};
    gameRoundMapping = {};
    descriptionRoundMapping = {};
    voteRoundMapping = {};
    
    // 保存状态
    saveToLocalStorage();
    
    // 开始单轮游戏
    startGameWithWords(undercoverWord, civilianWord, true);
}

// 游戏控制函数（保持向后兼容，但不再使用）
function startGame() {
    // 这个方法保留用于向后兼容，但实际应该使用 openMultiRoundModal()
    openMultiRoundModal();
}

function startRound() {
    fetch('/api/game/round/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(resp => {
        if (resp && resp.code === 200) {
            showAlert('success', resp.message || '回合已开始！');
            fetchGameState();
        } else {
            showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
        }
    })
    .catch(error => {
        showAlert('danger', '请求失败：' + error);
    });
}

function resetGame() {
    if (confirm('确定要重置游戏吗？这将重置所有游戏数据，但保留已注册的组。')) {
        fetch('/api/game/reset', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        })
        .then(response => response.json())
        .then(resp => {
            if (resp && resp.code === 200) {
                showAlert('success', resp.message || '游戏已重置');

                // 1. 清空前端的历史数据（描述、投票、结果）
                allVoteResults = {};
                allDescriptions = {};
                gameRoundMapping = {};
                descriptionRoundMapping = {};
                voteRoundMapping = {};

                // 2. 清空多轮配置
                totalRounds = 0;
                currentRoundIndex = 0;
                multiRoundConfig = null;
                nextRoundCheckDone = false;

                // 3. 清空 localStorage 中的游戏数据（保留注册信息）
                clearLocalStorageGameData();

                // 4. 立即更新显示
                updateDescriptions();      // 清空描述记录
                updateVoteRecords();       // 清空投票记录
                updateGameResults();       // 清空游戏结果
                updateGameStats();         // 更新统计（游戏次数、回合、最高分会重置）

                // 5. 从服务器获取最新状态（注册的组还在）
                fetchGameState();

                // 6. 清空词语输入框
                document.getElementById('undercover-word').value = '';
                document.getElementById('civilian-word').value = '';

                // 7. 手动重置统计显示（确保显示为0）
                document.getElementById('stat-games').textContent = '0';
                document.getElementById('stat-round').textContent = '0';
                document.getElementById('stat-highscore').textContent = '0';

            } else {
                showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
            }
        })
        .catch(error => {
            showAlert('danger', '请求失败：' + error);
        });
    }
}

// 只清除游戏相关的 localStorage 数据，不删除组信息
function clearLocalStorageGameData() {
    try {
        // 只清除游戏数据相关的键
        localStorage.removeItem(STORAGE_KEYS.VOTE_RESULTS);
        localStorage.removeItem(STORAGE_KEYS.DESCRIPTIONS);
        localStorage.removeItem(STORAGE_KEYS.ROUND_MAPPINGS);
        localStorage.removeItem(STORAGE_KEYS.MULTI_ROUND_CONFIG);
        localStorage.removeItem(STORAGE_KEYS.CURRENT_ROUND_INDEX);
        localStorage.removeItem(STORAGE_KEYS.TOTAL_ROUNDS);

        console.log('已清空游戏数据缓存');
    } catch (e) {
        console.error('清除 localStorage 游戏数据失败:', e);
    }
}

function clearAll() {
    if (confirm('确定要清空所有组和缓存吗？这将踢出所有已注册的组，就像新开了一次游戏一样。')) {
        fetch('/api/game/clear_all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        })
        .then(response => response.json())
        .then(resp => {
            if (resp && resp.code === 200) {
                showAlert('success', resp.message || '已清空所有组和缓存');
                // 清空所有历史数据
                allVoteResults = {};
                allDescriptions = {};
                gameRoundMapping = {};
                descriptionRoundMapping = {};
                voteRoundMapping = {};
                // 清空多轮配置
                totalRounds = 0;
                currentRoundIndex = 0;
                multiRoundConfig = null;
                nextRoundCheckDone = false;
                // 清除 localStorage
                clearLocalStorage();
                // 立即更新投票记录和游戏结果的显示
                updateVoteRecords();
                updateGameResults();
                fetchGameState();
                // 清除输入框
                document.getElementById('undercover-word').value = '';
                document.getElementById('civilian-word').value = '';
            } else {
                showAlert('danger', '错误：' + (resp ? resp.message : '后端无响应'));
            }
        })
        .catch(error => {
            showAlert('danger', '请求失败：' + error);
        });
    }
}
