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
        public int Id { get; set; }

        [Required]
        public int MemberId { get; set; }

        [Required]
        public string FullName { get; set; }

        [Required]
        [EmailAddress]
        public string Email { get; set; }

        [Required]
        public byte[] FaceImage { get; set; }

        [Required]
        public byte[] IdImage { get; set; }

        [Required]
        public RequestStatus status { get; set; } = RequestStatus.Pending;

        [Required]
        [Range(1,4)]
        public int AcademicYear { get; set; }

        [Required]
        public DateTime SubmittedAt { get; set; }

        // reviewdby [FK]
    }
}
