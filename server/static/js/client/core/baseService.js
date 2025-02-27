// core/BaseService.js
class BaseService {
    constructor() {
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;
        await this.initializeEvents();
        this.initialized = true;
    }

    async destroy() {
        if (!this.initialized) return;
        await this.removeEvents();
        this.initialized = false;
    }

    async enter() {
        await this.restoreState();
    }

    async leave() {
        await this.saveState();
    }

    initializeEvents() {}
    removeEvents() {}
    saveState() {}
    restoreState() {}
}