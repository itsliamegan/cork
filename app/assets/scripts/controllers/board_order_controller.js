export default class extends Stimulus.Controller {
	static targets = ["board", "list"]
	static values = { url: String }

	connect() {
		this.draggedBoard = null
		this.sourceList = null
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

		let board = event.currentTarget.closest(
			"[data-board-order-target=board]",
		)
		let list = board?.closest("[data-board-order-target=list]")
		if (!board || !list || !event.dataTransfer) {
			event.preventDefault()
			return
		}

		this.draggedBoard = board
		this.sourceList = list
		this.originalNextSibling = board.nextElementSibling
		this.hasMovedAway = false

		event.dataTransfer.effectAllowed = "move"
		event.dataTransfer.setData("text/plain", board.dataset.boardId)
		event.dataTransfer.setDragImage(board, event.offsetX, event.offsetY)

		requestAnimationFrame(() => {
			if (this.draggedBoard === board) {
				board.classList.add("frame-item--dragging")
			}
		})
	}

	dragOver(event) {
		if (
			this.saving ||
			!this.draggedBoard ||
			event.currentTarget !== this.sourceList
		) {
			return
		}

		event.preventDefault()
		event.dataTransfer.dropEffect = "move"

		let followingBoard = this.boardTargets
			.filter(
				(board) =>
					board !== this.draggedBoard && board.parentElement === this.sourceList,
			)
			.find((board) => {
				let bounds = board.getBoundingClientRect()
				return event.clientY < bounds.top + bounds.height / 2
			})

		let isOriginalPosition =
			(followingBoard ?? null) === this.originalNextSibling
		if (isOriginalPosition && !this.hasMovedAway) {
			this.removeDropIndicator()
			return
		}

		if (!isOriginalPosition) this.hasMovedAway = true
		this.ensureDropIndicator()
		this.sourceList.insertBefore(this.dropIndicator, followingBoard ?? null)
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
			!this.draggedBoard ||
			event.currentTarget !== this.sourceList
		) {
			return
		}

		event.preventDefault()
		if (!this.dropIndicator) {
			this.cleanupDrag()
			return
		}

		let boardId = event.dataTransfer?.getData("text/plain")
		if (boardId !== this.draggedBoard.dataset.boardId) {
			this.cleanupDrag()
			return
		}

		let board = this.draggedBoard
		let originalList = this.sourceList
		let originalNextSibling = this.originalNextSibling
		this.dropIndicator.replaceWith(board)
		this.dropIndicator = null
		let orderingChanged = board.nextElementSibling !== originalNextSibling
		this.cleanupDrag()

		if (!orderingChanged) return
		this.saving = true
		this.saveOrdering(board, originalList, originalNextSibling)
	}

	dragEnd() {
		this.cleanupDrag()
	}

	ensureDropIndicator() {
		if (this.dropIndicator) return
		this.dropIndicator = document.createElement("li")
		this.dropIndicator.className = "board-drop-target"
		this.dropIndicator.setAttribute("aria-hidden", "true")
	}

	removeDropIndicator() {
		this.dropIndicator?.remove()
		this.dropIndicator = null
	}

	cleanupDrag() {
		this.draggedBoard?.classList.remove("frame-item--dragging")
		this.removeDropIndicator()
		this.draggedBoard = null
		this.sourceList = null
		this.originalNextSibling = null
		this.hasMovedAway = false
	}

	async saveOrdering(board, originalList, originalNextSibling) {
		let body = new URLSearchParams()
		for (let orderedBoard of this.boardTargets) {
			body.append("board_id", orderedBoard.dataset.boardId)
		}

		try {
			let response = await fetch(this.urlValue, {
				method: "PUT",
				body,
			})
			if (!response.ok) throw new Error(`Could not save order: ${response.status}`)
		} catch (error) {
			if (originalNextSibling?.parentElement === originalList) {
				originalList.insertBefore(board, originalNextSibling)
			} else {
				originalList.append(board)
			}
			console.error(error)
		} finally {
			this.saving = false
		}
	}
}
