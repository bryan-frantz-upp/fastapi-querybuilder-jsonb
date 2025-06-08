// Mobile navigation toggle
document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector(".nav-toggle")
  const sidebar = document.querySelector(".sidebar")

  if (navToggle && sidebar) {
    navToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open")
    })

    // Close sidebar when clicking outside
    document.addEventListener("click", (e) => {
      if (!sidebar.contains(e.target) && !navToggle.contains(e.target)) {
        sidebar.classList.remove("open")
      }
    })
  }

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault()
      const target = document.querySelector(this.getAttribute("href"))
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        })

        // Close mobile sidebar after navigation
        if (window.innerWidth <= 1024) {
          sidebar.classList.remove("open")
        }
      }
    })
  })

  // Highlight current section in sidebar
  const observerOptions = {
    root: null,
    rootMargin: "-20% 0px -70% 0px",
    threshold: 0,
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        // Remove active class from all sidebar links
        document.querySelectorAll(".sidebar a").forEach((link) => {
          link.classList.remove("active")
        })

        // Add active class to current section link
        const currentLink = document.querySelector(`.sidebar a[href="#${entry.target.id}"]`)
        if (currentLink) {
          currentLink.classList.add("active")
        }
      }
    })
  }, observerOptions)

  // Observe all sections
  document.querySelectorAll("section[id]").forEach((section) => {
    observer.observe(section)
  })
})

// Copy code functionality
function copyCode(button) {
  const codeBlock = button.parentElement.querySelector("code")
  const text = codeBlock.textContent

  navigator.clipboard
    .writeText(text)
    .then(() => {
      const originalIcon = button.innerHTML
      button.innerHTML = '<i class="fas fa-check"></i>'
      button.style.background = "rgba(16, 185, 129, 0.2)"

      setTimeout(() => {
        button.innerHTML = originalIcon
        button.style.background = "rgba(255, 255, 255, 0.1)"
      }, 2000)
    })
    .catch((err) => {
      console.error("Failed to copy text: ", err)
    })
}

// Add active state styles for sidebar links
const style = document.createElement("style")
style.textContent = `
    .sidebar a.active {
        color: var(--primary-color);
        font-weight: 600;
        position: relative;
    }
    
    .sidebar a.active::before {
        content: '';
        position: absolute;
        left: -1.5rem;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 20px;
        background: var(--primary-color);
        border-radius: 2px;
    }
`
document.head.appendChild(style)

// Search functionality (basic implementation)
function initSearch() {
  const searchInput = document.createElement("input")
  searchInput.type = "text"
  searchInput.placeholder = "Search documentation..."
  searchInput.className = "search-input"

  const searchStyle = document.createElement("style")
  searchStyle.textContent = `
        .search-input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            font-size: 0.875rem;
            margin-bottom: 1rem;
            background: var(--background-color);
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .search-highlight {
            background: yellow;
            padding: 0.125rem;
            border-radius: 0.125rem;
        }
    `
  document.head.appendChild(searchStyle)

  const sidebarContent = document.querySelector(".sidebar-content")
  if (sidebarContent) {
    sidebarContent.insertBefore(searchInput, sidebarContent.firstChild)

    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase()
      const sections = document.querySelectorAll(".sidebar-section")

      sections.forEach((section) => {
        const links = section.querySelectorAll("a")
        let hasVisibleLinks = false

        links.forEach((link) => {
          const text = link.textContent.toLowerCase()
          if (text.includes(query)) {
            link.style.display = "block"
            hasVisibleLinks = true

            // Highlight matching text
            if (query) {
              const regex = new RegExp(`(${query})`, "gi")
              link.innerHTML = link.textContent.replace(regex, '<span class="search-highlight">$1</span>')
            } else {
              link.innerHTML = link.textContent
            }
          } else {
            link.style.display = query ? "none" : "block"
            link.innerHTML = link.textContent
          }
        })

        section.style.display = hasVisibleLinks || !query ? "block" : "none"
      })
    })
  }
}

// Initialize search when DOM is loaded
document.addEventListener("DOMContentLoaded", initSearch)

// Add scroll progress indicator
function addScrollProgress() {
  const progressBar = document.createElement("div")
  progressBar.className = "scroll-progress"

  const progressStyle = document.createElement("style")
  progressStyle.textContent = `
        .scroll-progress {
            position: fixed;
            top: var(--navbar-height);
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
            z-index: 1001;
            transition: width 0.1s ease;
        }
    `
  document.head.appendChild(progressStyle)
  document.body.appendChild(progressBar)

  window.addEventListener("scroll", () => {
    const scrollTop = window.pageYOffset
    const docHeight = document.body.scrollHeight - window.innerHeight
    const scrollPercent = (scrollTop / docHeight) * 100
    progressBar.style.width = scrollPercent + "%"
  })
}

document.addEventListener("DOMContentLoaded", addScrollProgress)
