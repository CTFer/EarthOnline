// 主应用入口
layui.use(["jquery", "layer", "form"], function () {
  const $ = layui.jquery;
  const layer = layui.layer;
  const form = layui.form;

  console.log("[Roadmap App] Initializing main application");

  // 全局变量，供模块使用
  window.$ = $;
  window.layer = layer;
  window.form = form;
  
  // 动态加载配置文件
  function loadScript(url, callback) {
    const script = document.createElement('script');
    script.src = url;
    script.type = 'text/javascript';
    script.onload = callback;
    // 添加错误处理，防止单个脚本加载失败导致整个应用崩溃
    script.onerror = function() {
      console.error(`[Roadmap App] Failed to load script: ${url}`);
      // 继续执行，避免阻塞其他脚本加载
      if (callback) callback();
    };
    document.head.appendChild(script);
  }
  
  // 加载顺序：config.js → utils.js → 所有模块文件
  const baseUrl = '/roadmap/static/js/client';
  
  loadScript(`${baseUrl}/config.js`, function() {
    console.log("[Roadmap App] Config loaded");
    
    loadScript(`${baseUrl}/utils.js`, function() {
      console.log("[Roadmap App] Utils loaded");
      
      // 加载所有模块文件
      const modules = [
        'themeManager',
        'authManager', 
        'taskManager',
        'formManager',
        'dragManager',
        'pinManager',
        'cycleTaskManager',
        'eventManager'
      ];
      
      let loadedModules = 0;
      
      modules.forEach(moduleName => {
        loadScript(`${baseUrl}/modules/${moduleName}.js`, function() {
          console.log(`[Roadmap App] Module ${moduleName} loaded`);
          loadedModules++;
          
          // 当所有模块加载完成后，初始化应用
          if (loadedModules === modules.length) {
            initApp();
          }
        });
      });
    });
  });
  
  // 初始化应用
  function initApp() {
    console.log("[Roadmap App] All dependencies loaded, initializing application");
    
    // 创建模块实例
    const themeManager = new ThemeManager();
    const authManager = new AuthManager();
    const taskManager = new TaskManager();
    const formManager = new FormManager();
    const dragManager = new DragManager();
    const pinManager = new PinManager();
    const cycleTaskManager = new CycleTaskManager();
    const eventManager = new EventManager();
    
    // 全局模块引用，供其他模块使用
    window.themeManager = themeManager;
    window.authManager = authManager;
    window.taskManager = taskManager;
    window.formManager = formManager;
    window.dragManager = dragManager;
    window.pinManager = pinManager;
    window.cycleTaskManager = cycleTaskManager;
    window.eventManager = eventManager;
    
    // 初始化所有模块
    function initAllModules() {
      console.log("[Roadmap App] Initializing all modules");
      
      // 初始化认证
      authManager.init();
      
      // 初始化周期任务功能
      cycleTaskManager.init();
      
      // 初始化置顶功能
      pinManager.init();
      
      // 初始化事件处理
      eventManager.init();
    }
    
    // 启动应用
    initAllModules();
    
    console.log("[Roadmap App] Application initialized successfully");
  }
});
