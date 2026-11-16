package org.acme.taskassigning.dto.input;

import java.util.List;

import org.acme.taskassigning.domain.Priority;
import org.eclipse.microprofile.openapi.annotations.media.Schema;

@Schema(description = "A task that must be assigned to an employee.")
public record TaskInputDTO(
        @Schema(description = "Unique identifier of the task.", required = true, minLength = 1) String id,
        @Schema(description = "Code of the task type of this task.", required = true, minLength = 1) String taskTypeCode,
        @Schema(description = "The index of this task among the tasks of the same task type, used only to tell "
                + "them apart in a human-readable way.", required = true, minimum = "0") Integer indexInTaskType,
        @Schema(description = "ID of the customer this task is for.", required = true, minLength = 1) String customerId,
        @Schema(description = "The earliest minute this task can start, relative to the start of the schedule.",
                required = true, minimum = "0") Long minStartTimeInMinutes,
        @Schema(description = "The priority of this task.", required = true) Priority priority,
        @Schema(description = "Tasks which must finish before this task starts.") List<String> predecessorIds) {
    public TaskInputDTO {
        predecessorIds = predecessorIds == null ? List.of() : List.copyOf(predecessorIds);
    }

    public TaskInputDTO(String id, String taskTypeCode, Integer indexInTaskType, String customerId,
            Long minStartTimeInMinutes, Priority priority) {
        this(id, taskTypeCode, indexInTaskType, customerId, minStartTimeInMinutes, priority, List.of());
    }
}
