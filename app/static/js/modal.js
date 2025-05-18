// Modal Utility
class Modal {
    constructor() {
        console.log('Modal: Initializing modal...');
        this.initializeElements();
        this.bindMethods();
        this.initializeEventListeners();
        console.log('Modal: Initialization complete');
    }

    initializeElements() {
        this.modal = document.getElementById('modal');
        this.modalTitle = document.getElementById('modal-title');
        this.modalBody = document.getElementById('modal-body');
        this.modalClose = document.querySelector('.modal-close');
        this.modalCancel = document.getElementById('modal-cancel');
        this.modalConfirm = document.getElementById('modal-confirm');
        this.resolve = null;
        this.reject = null;

        console.log('Modal elements initialized:', {
            modal: this.modal,
            modalTitle: this.modalTitle,
            modalBody: this.modalBody,
            modalClose: this.modalClose,
            modalCancel: this.modalCancel,
            modalConfirm: this.modalConfirm
        });
    }


    bindMethods() {
        this.show = this.show.bind(this);
        this.hide = this.hide.bind(this);
        this.handleClickOutside = this.handleClickOutside.bind(this);
        this.handleEscape = this.handleEscape.bind(this);
        this.cleanup = this.cleanup.bind(this);
    }


    initializeEventListeners() {
        // Close modal when clicking the X button
        if (this.modalClose) {
            this.modalClose.addEventListener('click', (e) => {
                e.preventDefault();
                this.hide();
                if (this.reject) this.reject(new Error('Modal was closed by user'));
            });
        }


        // Close modal when clicking outside the content
        if (this.modal) {
            this.modal.addEventListener('click', this.handleClickOutside);
        }


        // Close modal with Escape key
        document.addEventListener('keydown', this.handleEscape);
    }


    handleClickOutside(e) {
        if (e.target === this.modal) {
            this.hide();
            if (this.reject) this.reject(new Error('Clicked outside modal'));
        }
    }


    handleEscape(e) {
        if (e.key === 'Escape' && this.modal && this.modal.classList.contains('show')) {
            this.hide();
            if (this.reject) this.reject(new Error('Escape key pressed'));
        }
    }


    show({ 
        title = 'Alert', 
        message, 
        html = false, 
        confirmText = 'Confirm', 
        cancelText = 'Cancel',
        showCancel = true,
        onConfirm = null,
        onCancel = null
    } = {}) {
        console.log('Modal: Showing modal with options:', {
            title, message, confirmText, cancelText, showCancel
        });

        return new Promise((resolve, reject) => {
            try {
                this.resolve = resolve;
                this.reject = reject;

                // Set modal content
                if (this.modalTitle) this.modalTitle.textContent = title;
                
                if (this.modalBody) {
                    if (html) {
                        this.modalBody.innerHTML = message;
                    } else {
                        this.modalBody.textContent = message;
                    }
                }


                // Update buttons
                if (this.modalConfirm) {
                    this.modalConfirm.textContent = confirmText;
                    this.modalConfirm.onclick = (e) => {
                        e.preventDefault();
                        console.log('Modal: Confirm button clicked');
                        this.hide();
                        if (onConfirm) onConfirm();
                        resolve(true);
                    };
                }


                if (this.modalCancel) {
                    this.modalCancel.textContent = cancelText;
                    this.modalCancel.style.display = showCancel ? 'block' : 'none';
                    this.modalCancel.onclick = (e) => {
                        e.preventDefault();
                        console.log('Modal: Cancel button clicked');
                        this.hide();
                        if (onCancel) onCancel();
                        reject(new Error('Modal was cancelled'));
                    };
                }


                // Show modal
                console.log('Modal: Adding show class');
                if (this.modal) {
                    this.modal.style.display = 'flex';
                    this.modal.classList.add('show');
                    document.body.style.overflow = 'hidden';
                } else {
                    console.error('Modal element not found');
                    reject(new Error('Modal element not found'));
                }
            } catch (error) {
                console.error('Error showing modal:', error);
                reject(error);
            }
        });
    }


    hide() {
        console.log('Modal: Hiding modal');
        if (this.modal) {
            this.modal.classList.remove('show');
            this.modal.style.display = 'none';
            document.body.style.overflow = '';
            this.cleanup();
        }
    }


    cleanup() {
        console.log('Modal: Cleaning up');
        // Clear any existing event listeners
        if (this.modalConfirm) {
            this.modalConfirm.onclick = null;
        }
        if (this.modalCancel) {
            this.modalCancel.onclick = null;
        }
        
        // Reset the modal content
        if (this.modalTitle) this.modalTitle.textContent = '';
        if (this.modalBody) this.modalBody.innerHTML = '';
        
        // Reset promise handlers
        this.resolve = null;
        this.reject = null;
    }
}

// Initialize modal when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, initializing modal...');
    try {
        window.Modal = new Modal();
        console.log('Modal initialized successfully');
    } catch (error) {
        console.error('Failed to initialize modal:', error);
    }
});
