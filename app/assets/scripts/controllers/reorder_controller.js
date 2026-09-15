export default class extends Stimulus.Controller {
	static targets = ["item", "list"]
	static values = { field: String, url: String }

	connect() {
		this.draggedItem = null
		this.sourceList = null
		this.originalNextSibling = null
		this.dropIndicator = null
		this.hasMovedAway = false
		this.saving = false
	}

	disconnect() {
		this.cleanupDrag()
	}

	dragStart(event) {
		if (this.saving) {
			event.preventDefault()
			return
		}

		let item = event.currentTarget.closest("[data-reorder-target~=item]")
		let list = item?.closest("[data-reorder-target~=list]")
		if (!item || !list || !event.dataTransfer) {
			event.preventDefault()
			return
		}

		this.draggedItem = item
		this.sourceList = list
		this.originalNextSibling = item.nextElementSibling
		this.hasMovedAway = false

		event.dataTransfer.effectAllowed = "move"
		event.dataTransfer.setData("text/plain", item.dataset.reorderId)
		event.dataTransfer.setDragImage(item, event.offsetX, event.offsetY)

		requestAnimationFrame(() => {
			if (this.draggedItem === item) {
				item.classList.add("frame-item--dragging")
			}
		})
	}

	dragOver(event) {
		if (
			this.saving ||
			!this.draggedItem ||
			event.currentTarget !== this.sourceList
		) {
			return
		}

		event.preventDefault()
		event.dataTransfer.dropEffect = "move"

		let followingItem = this.itemTargets
			.filter(
				(item) =>
					item !== this.draggedItem && item.parentElement === this.sourceList,
			)
			.find((item) => {
				let bounds = item.getBoundingClientRect()
				return event.clientY < bounds.top + bounds.height / 2
			})

		let isOriginalPosition =
			(followingItem ?? null) === this.originalNextSibling
		if (isOriginalPosition && !this.hasMovedAway) {
			this.removeDropIndicator()
			return
		}

		if (!isOriginalPosition) this.hasMovedAway = true
		this.ensureDropIndicator()
		this.sourceList.insertBefore(this.dropIndicator, followingItem ?? null)
	}

	dragLeave(event) {
		if (event.currentTarget !== this.sourceList) return
		if (
			event.relatedTarget &&
			event.currentTarget.contains(event.relatedTarget)
		) {
			return
		}
		this.removeDropIndicator()
	}

	drop(event) {
		if (
			this.saving ||
			!this.draggedItem ||
			event.currentTarget !== this.sourceList
		) {
			return
		}

		event.preventDefault()
		if (!this.dropIndicator) {
			this.cleanupDrag()
			return
		}

		let itemId = event.dataTransfer?.getData("text/plain")
		if (itemId !== this.draggedItem.dataset.reorderId) {
			this.cleanupDrag()
			return
		}

		let item = this.draggedItem
		let originalList = this.sourceList
		let originalNextSibling = this.originalNextSibling
		this.dropIndicator.replaceWith(item)
		this.dropIndicator = null
		let orderingChanged = item.nextElementSibling !== originalNextSibling
		this.cleanupDrag()

		if (!orderingChanged) return
		this.saving = true
		this.saveOrdering(item, originalList, originalNextSibling)
	}

	dragEnd() {
		this.cleanupDrag()
	}

	ensureDropIndicator() {
		if (this.dropIndicator) return
		this.dropIndicator = document.createElement("li")
		this.dropIndicator.className = "reorder-drop-target"
		this.dropIndicator.setAttribute("aria-hidden", "true")
	}

	removeDropIndicator() {
		this.dropIndicator?.remove()
		this.dropIndicator = null
	}

	cleanupDrag() {
		this.draggedItem?.classList.remove("frame-item--dragging")
		this.removeDropIndicator()
		this.draggedItem = null
		this.sourceList = null
		this.originalNextSibling = null
		this.hasMovedAway = false
	}

	async saveOrdering(item, originalList, originalNextSibling) {
		let body = new URLSearchParams()
		for (let orderedItem of this.itemTargets) {
			body.append(this.fieldValue, orderedItem.dataset.reorderId)
		}

		try {
			let response = await fetch(this.urlValue, {
				method: "PUT",
				body,
			})
			if (!response.ok) {
				throw new Error(`Could not save order: ${response.status}`)
			}
		} catch (error) {
			if (originalNextSibling?.parentElement === originalList) {
				originalList.insertBefore(item, originalNextSibling)
			} else {
				originalList.append(item)
			}
			console.error(error)
		} finally {
			this.saving = false
		}
	}
}
