using System;
using System.Collections.Generic;
using System.Text;
using System.ComponentModel.DataAnnotations;
using Domain.Enums;

namespace Domain.Entities
{
    public class Registration_Request
    {
        [Key]
        int Id { get; set; }

        [Required]
        int MemberId { get; set; }

        [Required]
        string FullName { get; set; }

        [Required]
        [EmailAddress]
        string Email { get; set; }

        [Required]
        byte[] FaceImage { get; set; }

        [Required]
        byte[] IdImage { get; set; }

        [Required]
        RequestStatus status { get; set; } = RequestStatus.Pending;

        [Required]
        [Range(1,4)]
        int AcademicYear { get; set; }

        [Required]
        DateTime SubmittedAt { get; set; }

        // reviewdby [FK]
    }
}
